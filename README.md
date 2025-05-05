# Kubernetes Probes Demo - Comprehensive Guide

A hands-on laboratory exercise demonstrating how **readiness** and **liveness** probes function in real-world Kubernetes workloads.

## What This Demo Covers

* **HTTP-based probes** with a REST API service (`http-api` Deployment)
* **Exec-based probes** with a background worker (`exec-worker` Deployment)
* **Real dependency testing** with a Redis instance you can take up/down
* **Pre-built container images** available in Docker Hub repository:  
  `artisantek/probes`  
  ‑ `http-api-v1`  
  ‑ `exec-worker-v1`

## 1. Understanding Kubernetes Probes

Kubernetes probes are health-check mechanisms that determine the state of containers running in your pods. Properly configured probes help ensure application reliability and availability.

### 1.1 Probe Types Explained

| Probe Type | Purpose | Behavior | Failure Consequence |
|------------|---------|----------|---------------------|
| **Readiness** | Checks if the pod is ready to receive traffic | Runs periodically throughout the pod's lifecycle | Pod is marked as not ready and **removed from service endpoints** but continues running |
| **Liveness** | Detects if the application is running properly | Runs periodically throughout the pod's lifecycle | Container is **restarted** when the probe fails |
| **Startup** | Indicates if the application has started successfully | Runs at container startup only | Delays other probe checks until successful |

### 1.2 Probe Implementation Methods

Kubernetes supports three ways to implement probes:

* **`httpGet`**: Makes an HTTP request to a specified endpoint and considers success when the response code is between 200-399
* **`exec`**: Executes a command inside the container and considers success when the exit code is 0
* **`tcpSocket`**: Attempts to establish a TCP connection to a specified port and considers success when the connection is established

### 1.3 Important Probe Configuration Parameters

* **`initialDelaySeconds`**: Time to wait after container start before first probe
* **`periodSeconds`**: How often to perform the probe (default: 10 seconds)
* **`timeoutSeconds`**: How long to wait for probe to complete (default: 1 second)
* **`successThreshold`**: Minimum consecutive successes to be considered successful (default: 1)
* **`failureThreshold`**: Number of failures before taking action (default: 3)

## 2. Repository Structure

```
kubernetes-probes-demo/
├── docker/                  
│   ├── http-api/
│   └── exec-worker/
└── kubernetes/
    ├── redis.yaml
    ├── http-api.yaml
    └── exec-worker.yaml
```

## 3. Using Pre-built Images (Recommended)

This demo uses pre-built Docker images from Docker Hub:

* `artisantek/probes:http-api-v1` - FastAPI application with HTTP probe endpoints
* `artisantek/probes:exec-worker-v1` - Alpine container with Redis client

You can proceed directly to deployment with these pre-built images.

## 4. Building Images (Optional)

If you want to customize or rebuild the images, follow these steps:

### 4.1 HTTP API Image

```bash
# Build the HTTP API image
docker build -t <registry>/probes:http-api-v1 ./docker/http-api

# Push to Docker Hub (optional)
docker push <registry>/probes:http-api-v1
```

**What's in this image?**
- Python FastAPI application listening on port 8000
- Endpoints for `/ready` and `/live` health checks
- Control endpoints to simulate failures:
  - `/freeze` - Makes readiness probe fail
  - `/unfreeze` - Restores readiness 
  - `/crash` - Causes liveness probe to fail

### 4.2 Exec Worker Image

```bash
# Build the worker image
docker build -t artisantek/probes:exec-worker-v1 ./docker/exec-worker

# Push to Docker Hub (optional)
docker push artisantek/probes:exec-worker-v1
```

**What's in this image?**
- Alpine Linux with Redis client
- Shell script that periodically writes to Redis
- Liveness probe that checks Redis connectivity

## 5. Deploying to Kubernetes

### 5.1 Deploy Redis (Dependency)

```bash
kubectl apply -f k8s/redis.yaml
```

This creates:
- A Redis deployment with one replica
- A ClusterIP service exposing Redis on port 6379

### 5.2 Deploy the HTTP API

```bash
kubectl apply -f k8s/http-api.yaml
```

**Key components explained:**
```yaml
readinessProbe:
  httpGet:
    path: /ready    # Endpoint returns 200 when API is ready to serve traffic
    port: 8000
  initialDelaySeconds: 10  # Wait 10s after container starts before first probe
  periodSeconds: 5         # Check every 5 seconds
  failureThreshold: 3      # Allow 3 failures before marking not ready

livenessProbe:
  httpGet:
    path: /live     # Endpoint returns 200 when API is healthy
    port: 8000
  initialDelaySeconds: 20  # Give more time than readiness before checking
  periodSeconds: 10        # Check every 10 seconds
  failureThreshold: 3      # Allow 3 failures before restarting container
```

### 5.3 Deploy the Exec Worker

```bash
kubectl apply -f k8s/exec-worker.yaml
```

**Key components explained:**
```yaml
livenessProbe:
  exec:
    command:      # Run this command to check health
    - sh
    - -c
    - "redis-cli -h redis ping | grep PONG"  # Test Redis connectivity
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3    # Allow 3 failures before restarting
```

## 6. Verifying Deployment

Check that all pods are running correctly:

```bash
kubectl get pods
```

You should see output similar to:

```
NAME                          READY   STATUS    RESTARTS   AGE
http-api-6c8d95c5b6-x4jbn     1/1     Running   0          2m
exec-worker-75d9b9f9c-lqvz7   1/1     Running   0          2m
redis-5b589d9bf6-8kl2f        1/1     Running   0          2m
```

## 7. Hands-on Experiments

### 7.1 Simulate Readiness Probe Failure

```bash
# Get the name of the HTTP API pod
API=$(kubectl get pod -l app=http-api -o jsonpath='{.items[0].metadata.name}')

# Tell the API to simulate a readiness probe failure
kubectl exec $API -- curl -s -X POST http://localhost:8000/freeze

# Watch the pod status change
kubectl get pod $API -w
```

**What happens:**
- The pod's READY status changes from `1/1` to `0/1`
- The pod is removed from service endpoints (no traffic)
- The container is **not** restarted
- The pod remains in `Running` state

**Restore readiness:**
```bash
kubectl exec $API -- curl -s -X POST http://localhost:8000/unfreeze
```

### 7.2 Simulate Liveness Probe Failure

```bash
# Tell the API to simulate a liveness probe failure
kubectl exec $API -- curl -s -X POST http://localhost:8000/crash

# Watch the pod restart
kubectl get pods -w
```

**What happens:**
- The liveness probe fails
- After multiple failures (depending on `failureThreshold`), the container restarts
- The RESTARTS counter increments
- After restart, the container returns to normal operation

### 7.3 Break a Dependency (Redis)

```bash
# Scale down Redis to simulate an outage
kubectl scale deploy redis --replicas=0

# Watch how it affects the worker pod
kubectl get pods -w
```

**What happens:**
- The exec-worker pod's liveness probe fails (can't connect to Redis)
- The container restarts after `failureThreshold` failures
- The http-api pod remains Ready (it doesn't depend on Redis in this demo)

**Restore the dependency:**
```bash
kubectl scale deploy redis --replicas=1
```

## 8. Examining Probe Events

To see the exact reasons for probe failures:

```bash
kubectl describe pod $API | grep -A3 "probe failed"
```

This shows timestamped messages like:
```
  Warning  Unhealthy  2m (x3 over 3m)  kubelet  Readiness probe failed: HTTP probe failed with statuscode: 503
  Warning  Unhealthy  30s (x3 over 1m)  kubelet  Liveness probe failed: HTTP probe failed with statuscode: 500
```

## 9. Clean-up

Remove all resources created for this demo:

```bash
kubectl delete -f k8s/exec-worker.yaml
kubectl delete -f k8s/http-api.yaml
kubectl delete -f k8s/redis.yaml
```

## 10. Advanced Probe Configurations

Here are some additional configurations to explore:

### 10.1 Fine-tuning Probe Timing

```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 30    # Wait longer for initial ready state
  periodSeconds: 10          # Check less frequently
  timeoutSeconds: 3          # Allow more time for endpoint to respond
  successThreshold: 2        # Require two successes to mark ready
  failureThreshold: 5        # Allow more failures before action
```

### 10.2 Adding a Startup Probe

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8000
  failureThreshold: 30       # Allow up to 30 failures
  periodSeconds: 10          # 10s between checks (total 300s grace period)
```

### 10.3 Complex Exec Probe Example

```yaml
livenessProbe:
  exec:
    command:
    - sh
    - -c
    - |
      if [ -f /tmp/healthy ]; then
        exit 0
      else
        exit 1
      fi
```

## 11. Best Practices for Production

1. **Set appropriate timeouts**: Ensure probe timeouts are shorter than your probe period
2. **Configure graceful initialDelaySeconds**: Give containers enough time to initialize
3. **Use distinctive endpoints** for readiness vs. liveness
4. **Keep probe checks lightweight** to avoid performance impact
5. **Separate dependency checks** from application health checks
6. **Consider startup probes** for slow-starting applications
7. **Test failure scenarios** before going to production

Happy probing! 🚀