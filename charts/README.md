## Deploy on Kubernetes
### Note: this deployment requires an existing Amazon EKS cluster

Download and configure the AWS CLI with instructions [here](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
```
aws configure
AWS Access Key ID [None]: <insert key> (from account)
AWS Secret Access Key [None]: <insert secret key> (from account)
Default region name [None]: us-east-1
Default output format [None]: json
```

Download Kubectl:

- [Windows](https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl-on-windows)
- Mac
    ```
    brew install kubectl
    ```

Download Helm:
- [Windows](https://github.com/helm/helm/releases)
- Mac
    ```
    brew install helm
    ```

### For a new deployment
From the charts directory:
```
helm install --generate-name persistentvolumes
helm install --generate-name seed
```

Configure kubeconfig
```
aws eks --region us-east-1 update-kubeconfig --name seed
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
Note: the service will restart the pod and re-pull the image

Common kubectl actions can be found [here](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
