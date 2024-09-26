# jenkins-ci

1. Setup Jenkins
- Create an EC2 instance with Ubuntu AMI and below user data:
```
#!/bin/bash

//install java
sudo apt install default-jre
sudo apt install default-jdk

// install jenkins
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key |sudo gpg --dearmor -o /usr/share/keyrings/jenkins.gpg
sudo sh -c 'echo deb [signed-by=/usr/share/keyrings/jenkins.gpg] http://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt update
sudo apt install jenkins
sudo systemctl start jenkins.service

//install docker
sudo apt install docker.io
sudo usermod -aG docker $USER
sudo chmod 666 /var/run/docker.sock
sudo systemctl restart jenkins

// install git
sudo apt install git

// install aws cli
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt-get install -y unzip
unzip awscliv2.zip
sudo ./aws/install

```

- Config security to open port 22 (for SSH), and 8080 (for Jenkins) from your IP address

- Access Jenkins server with http://CREATED_INSTANCE_PUBLIC_IP:8080

- It will ask for password so you will need to SSH to the instance and run this command:
```
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

- Install needed plugin (include Github Plugin)and create first admin account 

- For setup AWS credential for Jenkins, use IAM Role (because the pipeline will push image to ECR so it will need ECR access as below. It's not least priviedge yet)
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateServiceLinkedRole"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "iam:AWSServiceName": [
                        "replication.ecr.amazonaws.com"
                    ]
                }
            }
        }
    ]
}
```

- Go to Manage Jenkins -> System and go to the end of the page to setup Email Notification (for send mail when build failed) with following info (username is the mail want the notificatio send from, password is the app password - You can reference here (https://support.google.com/mail/thread/205453566/how-to-generate-an-app-password?hl=en)):
![image](https://github.com/user-attachments/assets/766fc2a1-f966-4533-a1bc-4fcdff1a35ad)


2. Create Jenkins Pipeline 

- Jenkins pipeline definition - This will checkout, build image and push to ECR repo, test dump test - if failed, it will send mail to the setup email
```
pipeline {
    agent any
    environment {
        AWS_ACCOUNT_ID = "your-account"
        AWS_DEFAULT_REGION = "image-region"
        IMAGE_REPO_NAME = "image-repo"
    }
   
    stages {
        
        stage('Cloning Git') {
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: '', url: 'your github repo url']]])     
            }
        }

        stage('Logging into AWS ECR') {
            steps {
                script {
                    sh """aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"""
                }  
            }
        }
        
        stage('Building image') {
            steps {
                script {
                    sh """ docker build -t ${IMAGE_REPO_NAME}:${env.BUILD_NUMBER} ."""
                }
            }
        }
   
        stage('Pushing to ECR') {
            steps {  
                script {
                    sh """docker tag ${IMAGE_REPO_NAME}:${env.BUILD_NUMBER} ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${IMAGE_REPO_NAME}:${env.BUILD_NUMBER}"""
                    sh """docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${IMAGE_REPO_NAME}:${env.BUILD_NUMBER}"""
                }
            }
        }
        stage('Test') { 
          steps { 
            sh 'python3 dump_test.py'
          } 
        }
    }
    post { 
    always { 
        echo 'The pipeline completed'
    } 
    success {                    
        echo "Flask Application Up and running!!"
    } 
    failure { 
        echo 'Build stage failed'
        mail bcc: '', body: "<b>Failed</b><br>Project: ${env.JOB_NAME} <br>Build Number: ${env.BUILD_NUMBER} <br> URL build project: ${env.BUILD_URL}", cc: '', charset: 'UTF-8', from: '', mimeType: 'text/html', replyTo: '', subject: "ERROR CI: ${env.JOB_NAME}", to: "your email";  

    } 
  } 
}
```

- Setup trigger when push

+ Config webhook for your repo with http://CREATED_INSTANCE_PUBLIC_IP:8080/github-webhook/ with content type as application/json. Then come to your Jenkins with your pipeline, enable GitHub hook trigger for GITScm polling

3. Test the Pipeline
- Push new code and check the pipeline.

4. Setup updatemanifest github and Jenkins pipeline

- Create github repo with file "flask_demo.yaml" (can be any name you want, but for this tutor, it's flask_demo.yaml) - this repo is called as manifest-repo for following tutorial. This file will contain define for the deployment with flask-app  and a load balancer that have a target group connect to this flask-app.

```
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: flask-app
  name: flask-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flask-app
  strategy: {}
  template:
    metadata:
      labels:
        app: flask-app
    spec:
      containers:
      - image: your-account.dkr.ecr.your-region.amazonaws.com/your-ecr-repo:your-tag
        name: flask-app
        resources: {}
status: {}
---
apiVersion: v1
kind: Service
metadata:
  name: lb-service
  labels:
    app: lb-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5000
  selector:
    app: flask-app
```

- Create updatemanifest Jenkins pipeline, put this following pipeline definition. This will change the image with the tag that send in DOCKERTAG parameter in flask_demo.yaml and then will push this updated file to the repo:
```
pipeline {
    agent any
    environment {
        AWS_ACCOUNT_ID = "your-account"
        AWS_DEFAULT_REGION = "image-region"
        IMAGE_REPO_NAME = "image-repo"
        MANIFEST_REPO = "your-manifest-repo"
        GITHUB_CREDENTIAL_ID = "your-credential-id"
    }
    stages {
        
        stage('Cloning Git') {
            steps {
                checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: '', url: 'your-manifest-repo']]])     
            }
        }
        
        stage('Update GIT') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: ${GITHUB_CREDENTIAL_ID}, passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME')]) {
                        sh "git config user.email your-repo-email"
                        sh "git config user.name your-name"
                        sh "sed -i 's+${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${IMAGE_REPO_NAME}.*+${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${IMAGE_REPO_NAME}:${DOCKERTAG}+g' flask_demo.yaml"
                        sh "git add ."
                        sh "git commit -m 'Done by Jenkins Job changemanifest: ${env.BUILD_NUMBER}'"
                        sh "git push https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/${GIT_USERNAME}/{MANIFEST_REPO}.git HEAD:master"
                    }
                }
            }
        }
    }
}
``` 
- Because it will push code to the repo, so it will need to config credential github for it. Create a github credential with this tutorial: https://www.geeksforgeeks.org/how-to-add-git-credentials-in-jenkins/

- Set the pipeline with have parameter DOCKERTAG like below:
![image](https://github.com/user-attachments/assets/e698aca8-e986-415b-9b4c-223fc862c852)


- Update Jenkins to build and test with this stage:

```
stage('Trigger ManifestUpdate') {
    steps {
        echo "triggering updatemanifestjob"
        build job: 'updatemanifest', parameters: [string(name: 'DOCKERTAG', value: env.BUILD_NUMBER)]
    }
}
```

5. Setup EKS

- Create a EC2 install to run eksctl command on it (can run on local but not prefer setup credential on local)

- Open port to 22 to SSH to the instance

- Run following commands:
```
\\ install eksctl
export ARCH=amd64
export PLATFORM=$(uname -s)_$ARCH
curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$PLATFORM.tar.gz"
curl -sL "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_checksums.txt" | grep $PLATFORM | sha256sum --check
tar -xzf eksctl_$PLATFORM.tar.gz -C /tmp && rm eksctl_$PLATFORM.tar.gz
sudo mv /tmp/eksctl /usr/local/bin

\\ install aws cli
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt-get install -y unzip
unzip awscliv2.zip
sudo ./aws/install

\\ install kubectl
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

\\ create eks-cluster
eksctl create cluster --name your-eks-cluster-name --region your-region --version 1.29

\\ update kube config
aws eks update-kubeconfig --region your-region --name your-eks-cluster-name



\\ Create ArgoCD

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

```

- Because this is a public repo, or else you will need to config github credential for Argo
```
\\ Install ArgoCD CLI
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd

argocd repo add your-repo --username <username> --password <password>
```

- Create manifest file:

```
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
    name: flask-app
    namespace: argocd
spec:
    project: default
    source:
    repoURL: your-manifest-repo
    path: ./
    targetRevision: HEAD
    destination:
    server: https://kubernetes.default.svc
    namespace: default
    syncPolicy:
    automated:
        prune: false
        selfHeal: false
```

- Run command to deploy application to Argo
```
kubectl apply -f your-application.yaml
```

- Because setup it to sync automately, so ArgoCD will detect change from manifest repo and then sync the update.

6. Test Pipeline

- Add a new code and see if it's updated.
