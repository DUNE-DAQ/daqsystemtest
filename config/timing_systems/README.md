If using bristol or iceberg configurations, an instance of the connectivity service needs to be started, e.g.: 
```
gunicorn -b 0.0.0.0:15432 --workers=1 --worker-class=gthread --threads=4 --timeout 5000000000 connection-service.connection-flask:app
```
The timing sessions do not start the connectivity service because they apply a port offset. The CERN configurations make use of the already existing NP04 connectivity service.