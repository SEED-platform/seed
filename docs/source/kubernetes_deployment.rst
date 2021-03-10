Kubernetes Deployment Guide with Helm
=====================================

Kubernetes is a robust container orchestration system for easy application deployment and management.  Helm takes that a step further with by packaging up required helm "charts" into one deployment command.

Setup
-----

Cluster
^^^^^^^

In order to deploy the SEED platform on a Kubernetes you will need "cluster" which will be configured by your cloud service of choice.  Each installation will be slightly different depending on the service.
Bellow are links to quick-start guides for provisioning a cluster and connecting.

* Amazon Web Services (`AWS`_)
* Google Cloud Platform (`GCP`_)
* Azure (`AKS`_)

.. _AWS: https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html
.. _GCP: https://cloud.google.com/kubernetes-engine/docs/quickstart
.. _AKS: https://docs.microsoft.com/en-us/azure/aks/kubernetes-walkthrough#connect-to-the-cluster

Kubectl
^^^^^^^

Kubectl is the main function in which you will be interfacing with your deployed application on your cluster.  This CLI is what connects you to your cluster that you have just provisioned.
If your cloud service did not have you configure kubectl in your cluster setup, you can download it `here`_.  Once kubectl is installed and configured to your cluster
you can run some simple commands to ensure its working properly:

.. code-block:: console

    #View the cluster
    kubectl cluster-info

    #View pods, services and replicasets (will be empty until deploying an app)
    kubectl get all

All of the common kubectl commands can be found in these `docs`_

.. _docs: https://kubernetes.io/docs/reference/kubectl/cheatsheet/

.. note:: For those unfamiliar with CLIs, there are a number of GUI applications that are able to deploy on your stack with ease.  One of which is Kubernetes native application called `Dashboard UI`_

.. _here: https://kubernetes.io/docs/tasks/tools/
.. _Dashboard UI: https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/

Helm
^^^^
Helm organizes all of your Kubernetes deployment, service, and volume yml files into "charts" that can be deployed, managed, and published with simple commands.
To install Helm:

* `Windows`_
* Mac (with Homebrew) :code:`brew install helm`


.. _Windows: https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl-on-windows

Charts
^^^^^^
SEED stores its charts in the `charts directory`_ of the Github Repo.  There are two main charts that are deployed when starting SEED on Kubernetes.

* persistentvolumes - these are the volumes to store SEED media data and SEED Postgres data
* seed - this stores all of the other deployemnt and service files for the application

Unlike persistentvolumes, the seed charts must be modified with user environment variables that will be forwarded to the docker container for deployment.
Before deployment, the user **MUST** set these variables to their desired values.

web-deployment.yaml
*******************
This chart contains the deployment specification for the SEED web container.  Replace all the values in </>.

.. code-block:: yaml

    # Environment variables for the web container
    - env:
        # AWS Email service variables to send emails to new users - can be removed if not using this functionality.
        - name: AWS_ACCESS_KEY_ID
          value: <access_key_id>
        - name: AWS_SECRET_ACCESS_KEY
          value: <secret_access_key>
        - name: AWS_SES_REGION_NAME
          value: us-west-2
        - name: AWS_SES_REGION_ENDPOINT
          value: email.us-west-2.amazonaws.com
        - name: SERVER_EMAIL
          value: info@seed-platform.org
        # Django Variables
        - name: DJANGO_SETTINGS_MODULE
          value: config.settings.docker
        - name: SECRET_KEY
          value: <replace-secret-key>
        - name: SEED_ADMIN_ORG
          value: default
        - name: SEED_ADMIN_PASSWORD
          value: <super-secret-password>
        - name: SEED_ADMIN_USER
          value: <user@seed-platform.org>
        # Postgres variables
        - name: POSTGRES_DB
          value: seed
        - name: POSTGRES_PASSWORD
          value: <super-secret-password> # must match db-postgres-deployment.yaml and web-celery-deployment.yaml
        - name: POSTGRES_PORT
          value: "5432"
        - name: POSTGRES_USER
          value: seeduser
        # Bsyncr analysis variables
        - name: BSYNCR_SERVER_PORT
          value: "5000"
        - name: BSYNCR_SERVER_HOST
          value: bsyncr
        # Sentry monitoring - remove if not applicable
        - name: SENTRY_JS_DSN
          value: <enter-dsn>
        - name: SENTRY_RAVEN_DSN
          value: <enter-dsn>
        # Google self registration security - remove if not applicable
        - name: GOOGLE_RECAPTCHA_SECRET_KEY
          value: <reCAPTCHA-key>
        # Toggles the v2 version of the SEED API
        - name: INCLUDE_SEED_V2_APIS
          value: TRUE
        image: seedplatform/seed:<insert deployment image version>
        #versions can be found here https://github.com/SEED-platform/seed/releases/tag/v2.9.3

web-celery-deployment.yaml
**************************
This chart contains the deployment specification for the Celery container to connect to Postgres.  Replace the Postgres password to match web-deployment.

.. code-block:: yaml

        - name: POSTGRES_PASSWORD
          value: <super-secret-password> # must match db-postgres-deployment.yaml and web-celery-deployment.yaml

bsyncr-deployment.yaml
**************************
This chart contains the deployment specification for the bsyncr analysis server.  Request a NOAA token from `this website`_.

.. _this website: https://www.ncdc.noaa.gov/cdo-web/token

.. code-block:: yaml

          - name: NOAA_TOKEN
            value: <token>

.. _charts directory: https://github.com/SEED-platform/seed/tree/develop/charts

Deployment
^^^^^^^^^^
Once you are connected to your cluster and have your settings configured with the environment variables of you choice in the charts, you are ready to deploy the app.
This will be done using helm commands in the root of the charts directory.

* :code:`helm install --generate-name persistentvolumes`
* :code:`helm install --generate-name seed`

You will be able to see SEED coming online with statuses like container creating, and running with:

* :code:`kubectl get all`

Once all of the pods are running you will be able to hit the external ingress through the URL listed in the web service information. It should look something like
:code:`service/web           LoadBalancer   10.100.154.227   <my-unique-url>   80:32291/TCP`

Logging In
^^^^^^^^^^
After a successful deployment in order to login you will need to create yourself as a user in the web container.  To do this, we will exec into the container and run some Django commands.
* :code:`kubectl get pods`
* :code:`kubectl exec -it pod/<my-pods-id> bash`

Now that we are in the container, we can make a user.
.. code-block:: bash

    ./manage.py create_default_user --username=admin@my.org --organization=seedorg --password=badpass

You can now use these credentials to log in to the SEED website.





