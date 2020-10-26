## Deploy on Kubernetes
### Note: this deployment requires an existing Amazon EKS cluster

Download and configure the AWS CLI with instructions [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
```
aws configure
AWS Access Key ID [None]: <insert key> (from account)
AWS Secret Access Key [None]: <insert secret key> (from account)
Default region name [None]: us-east-1
Default output format [None]: json
```

Download Kubectl:
```
brew install kubectl
```

Download Helm:
```
brew install helm
```

### For a new deployment
From the charts directory:
```
helm install --generate-name persistentvolumes
helm install --generate-name seed
```

View the deployments and services
```
kubectl get all
```

### For an existing deployment
Update the web container
```
kubectl delete pod/web-<assigned-hash>
```
Note: the service will restart the pod an re-pull the image

Common kubectl actions can be found [here](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

