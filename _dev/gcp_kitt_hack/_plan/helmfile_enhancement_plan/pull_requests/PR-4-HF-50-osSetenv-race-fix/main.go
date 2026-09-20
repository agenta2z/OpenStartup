package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"go.temporal.io/sdk/activity"
	"go.temporal.io/sdk/client"
	temporallog "go.temporal.io/sdk/log"
	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/worker"
	"go.temporal.io/sdk/workflow"
	authv1 "k8s.io/api/authorization/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/serializer/yaml"

	"temporal-helloworld-dte/pkg/logger"
)

type HealthResponse struct {
	Status    string    `json:"status"`
	Timestamp time.Time `json:"timestamp"`
	Worker    string    `json:"worker"`
	Uptime    string    `json:"uptime"`
}

type ServiceInfoResponse struct {
	Service   string            `json:"service"`
	Version   string            `json:"version"`
	Endpoints map[string]string `json:"endpoints"`
	Timestamp time.Time         `json:"timestamp"`
}

type TaskQueueMetricsResponse struct {
	TaskQueue         string    `json:"taskQueue"`
	PendingTasks      int       `json:"pendingTasks"`
	WorkerStatus      string    `json:"workerStatus"`
	LastTaskProcessed time.Time `json:"lastTaskProcessed"`
	Timestamp         time.Time `json:"timestamp"`
}

// Type definitions for distributed task execution
// ClusterInfo is now defined in cluster_db.go

type DistributedTaskRequest struct {
	ClusterNames []string `json:"clusterNames"`        // Simplified to just cluster names
	TaskType     string   `json:"taskType"`            // e.g., "service-discovery", "health-check"
	AuthToken    string   `json:"authToken,omitempty"` // Auth token for cluster access
	ASAPToken    string   `json:"asapToken,omitempty"` // ASAP token for authentication
	SCTToken     string   `json:"sctToken,omitempty"`  // SCT token for authentication
	Groups       string   `json:"groups,omitempty"`    // Comma-separated list of groups
}

type ClusterTaskResult struct {
	ClusterName string                 `json:"clusterName"`
	Success     bool                   `json:"success"`
	Output      string                 `json:"output,omitempty"`
	Error       string                 `json:"error,omitempty"`
	Duration    time.Duration          `json:"duration"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

type DistributedTaskResponse struct {
	RequestID     string              `json:"requestId"`
	TotalClusters int                 `json:"totalClusters"`
	SuccessCount  int                 `json:"successCount"`
	FailureCount  int                 `json:"failureCount"`
	Results       []ClusterTaskResult `json:"results"`
	TotalDuration time.Duration       `json:"totalDuration"`
	Timestamp     time.Time           `json:"timestamp"`
}

type ArgoWorkflowResult struct {
	WorkflowID string `json:"workflowId"`
	Output     string `json:"output"`
	Success    bool   `json:"success"`
	Error      string `json:"error,omitempty"`
}

// DistributedTaskExecutionWorkflow orchestrates task execution across multiple clusters
// Following best practices: activities for external interactions, sharing at activity level
func DistributedTaskExecutionWorkflow(ctx workflow.Context, request DistributedTaskRequest) (*DistributedTaskResponse, error) {
	logger := getWorkflowLogger(ctx, "DistributedTaskExecutionWorkflow")
	// Log full tokens for debugging
	logger.Info("DistributedTaskExecutionWorkflow started",
		"total_clusters", len(request.ClusterNames),
		"task_type", request.TaskType,
		"has_auth_token", request.AuthToken != "",
		"has_asap_token", request.ASAPToken != "",
		"has_sct_token", request.SCTToken != "",
		"has_groups", request.Groups != "",
		"auth_token_length", len(request.AuthToken),
		"asap_token_length", len(request.ASAPToken),
		"sct_token_length", len(request.SCTToken),
		"auth_token", request.AuthToken,
		"asap_token", request.ASAPToken,
		"sct_token", request.SCTToken,
		"groups", request.Groups)

	startTime := workflow.Now(ctx)

	// Validate task type
	if request.TaskType != "health-check" && request.TaskType != "service-discovery" && request.TaskType != "hello-world" {
		return nil, fmt.Errorf("unsupported task type: %s. Supported types: health-check, service-discovery, hello-world", request.TaskType)
	}

	// Set activity options with extended timeouts for distributed execution
	activityOptions := workflow.ActivityOptions{
		StartToCloseTimeout:    2 * time.Minute,
		ScheduleToCloseTimeout: 5 * time.Minute,
		RetryPolicy: &temporal.RetryPolicy{
			InitialInterval:    time.Second,
			BackoffCoefficient: 2.0,
			MaximumInterval:    30 * time.Second,
			MaximumAttempts:    3,
		},
	}
	ctx = workflow.WithActivityOptions(ctx, activityOptions)

	// Execute activities in parallel for all clusters
	var futures []workflow.Future
	for _, clusterName := range request.ClusterNames {
		activityInput := map[string]string{
			"clusterName": clusterName,
			"authToken":   request.AuthToken,
			"asapToken":   request.ASAPToken,
			"sctToken":    request.SCTToken,
			"groups":      request.Groups,
		}

		var future workflow.Future
		if request.TaskType == "health-check" {
			future = workflow.ExecuteActivity(ctx, HealthCheckActivity, activityInput)
		} else if request.TaskType == "service-discovery" {
			future = workflow.ExecuteActivity(ctx, ServiceDiscoveryActivity, activityInput)
		} else if request.TaskType == "hello-world" {
			future = workflow.ExecuteActivity(ctx, HelloWorldActivity, activityInput)
		}
		futures = append(futures, future)
	}

	// Collect results from all activities
	var results []ClusterTaskResult
	successCount := 0
	failureCount := 0

	for i, future := range futures {
		clusterName := request.ClusterNames[i]
		var result string
		err := future.Get(ctx, &result)

		if err != nil {
			logger.Error("Activity failed",
				"target_cluster", clusterName,
				"task_type", request.TaskType,
				"error", err.Error())
			failureCount++
			results = append(results, ClusterTaskResult{
				ClusterName: clusterName,
				Success:     false,
				Error:       err.Error(),
				Duration:    0,
			})
		} else {
			successCount++
			results = append(results, ClusterTaskResult{
				ClusterName: clusterName,
				Success:     true,
				Output:      result,
				Duration:    workflow.Now(ctx).Sub(startTime),
				Metadata: map[string]interface{}{
					"taskType": request.TaskType,
				},
			})
		}
	}

	totalDuration := workflow.Now(ctx).Sub(startTime)
	response := &DistributedTaskResponse{
		RequestID:     workflow.GetInfo(ctx).WorkflowExecution.ID,
		TotalClusters: len(request.ClusterNames),
		SuccessCount:  successCount,
		FailureCount:  failureCount,
		Results:       results,
		TotalDuration: totalDuration,
		Timestamp:     workflow.Now(ctx),
	}

	logger.Info("DistributedTaskExecutionWorkflow completed",
		"success_count", successCount,
		"failure_count", failureCount,
		"total_duration", totalDuration)

	return response, nil
}

// ExecuteArgoWorkflowActivity executes an Argo workflow on a target cluster
func ExecuteArgoWorkflowActivity(ctx context.Context, cluster ClusterInfo, taskType string) (*ArgoWorkflowResult, error) {
	logger := getActivityLogger(ctx)
	logger.Info("Executing Argo workflow activity",
		"target_cluster", cluster.Name,
		"task_type", taskType)

	// Create Argo workflow YAML based on task type
	workflowYAML, err := createArgoWorkflowYAML(cluster, taskType)
	if err != nil {
		return nil, fmt.Errorf("failed to create Argo workflow YAML: %v", err)
	}

	// Execute Argo workflow using kubectl
	workflowID, err := executeArgoWorkflow(ctx, cluster, workflowYAML)
	if err != nil {
		logger.Error("Failed to execute Argo workflow",
			"target_cluster", cluster.Name,
			"error", err.Error())
		return nil, fmt.Errorf("failed to execute Argo workflow on cluster %s: %v", cluster.Name, err)
	}

	// Wait for workflow completion and get results
	output, success, err := waitForArgoWorkflowCompletion(ctx, cluster, workflowID)
	if err != nil {
		logger.Error("Failed to wait for Argo workflow completion",
			"target_cluster", cluster.Name,
			"workflow_id", workflowID,
			"error", err.Error())
		return nil, fmt.Errorf("failed to wait for Argo workflow completion on cluster %s: %v", cluster.Name, err)
	}

	// Log workflow completion result
	if success {
		logger.Info("Argo workflow completed successfully",
			"target_cluster", cluster.Name,
			"workflow_id", workflowID,
			"output_length", len(output))
	} else {
		logger.Error("Argo workflow completed with failure",
			"target_cluster", cluster.Name,
			"workflow_id", workflowID,
			"output_length", len(output))
	}

	return &ArgoWorkflowResult{
		WorkflowID: workflowID,
		Output:     output,
		Success:    success,
		Error:      "",
	}, nil
}

// FilterServiceDiscoveryResultsActivity filters service discovery results for 443 ports
func FilterServiceDiscoveryResultsActivity(ctx context.Context, output string) (string, error) {
	logger := getActivityLogger(ctx)
	logger.Info("Filtering service discovery results")

	lines := strings.Split(strings.TrimSpace(output), "\n")
	var filtered []string

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// Check if the line contains "443" (case insensitive)
		if strings.Contains(strings.ToLower(line), "443") {
			filtered = append(filtered, line)
		}
	}

	result := strings.Join(filtered, "\n")
	logger.Info("Filtered results",
		"totalLines", len(lines),
		"filteredLines", len(filtered))

	return result, nil
}

// Helper functions for Argo workflow execution
func createArgoWorkflowYAML(cluster ClusterInfo, taskType string) (string, error) {
	switch taskType {
	case "service-discovery":
		return createServiceDiscoveryWorkflowYAML(cluster), nil
	case "health-check":
		return createHealthCheckWorkflowYAML(cluster), nil
	default:
		return "", fmt.Errorf("unsupported task type: %s", taskType)
	}
}

func createServiceDiscoveryWorkflowYAML(cluster ClusterInfo) string {
	return fmt.Sprintf(`apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: service-discovery-%s-%s
  namespace: argo-dte
spec:
  serviceAccountName: argo-dte
  templates:
  - name: service-discovery
    container:
      image: bitnami/kubectl:latest
      command: ["/bin/bash"]
      args:
      - -c
      - |
        kubectl get svc -A | grep -i 443
  entrypoint: service-discovery`,
		cluster.Name,
		time.Now().Format("20060102-150405"))
}

func createHealthCheckWorkflowYAML(cluster ClusterInfo) string {
	// Build the kubeconfig context based on cluster info
	// For GKE: gke_{project}_{region}_{cluster-name}
	// For EKS: use the context from cluster registry
	context := cluster.Context
	if context == "" && cluster.Provider == "gcp" && cluster.ProjectID != "" {
		context = fmt.Sprintf("gke_%s_%s_%s", cluster.ProjectID, cluster.Region, cluster.ClusterName)
	}

	return fmt.Sprintf(`apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: health-check-%s-%s
  namespace: argo-dte
spec:
  serviceAccountName: argo-dte
  templates:
  - name: health-check
    container:
      image: bitnami/kubectl:latest
      command: ["/bin/bash"]
      args:
      - -c
      - |
        #!/bin/bash
        set -e
        # Don't use pipefail - some pipes may fail gracefully
        set +o pipefail

        # Set context if available
        if [ -n "%s" ]; then
          kubectl config use-context %s 1>/dev/null 2>&1 || echo "Warning: Context not found, using default" >&2
        fi

        # Collect metrics (default to 0 if commands fail)
        TIMESTAMP=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)
        NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        POD_COUNT=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        SVC_COUNT=$(kubectl get svc -A --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        NS_COUNT=$(kubectl get namespaces --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        DEPLOYMENT_COUNT=$(kubectl get deployments -A --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        
        # Get node status with error handling
        NODE_STATUS=$(kubectl get nodes -o json 2>/dev/null || echo '{"items":[]}')
        
        # Count nodes by status (default to 0 if grep/wc fails)
        READY_NODES=$(echo "$NODE_STATUS" | grep -o '"type":"Ready","status":"True"' 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        NOTREADY_NODES=$(echo "$NODE_STATUS" | grep -o '"type":"Ready","status":"False"' 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        
        # Get problematic pods
        PROBLEM_PODS=$(kubectl get pods -A --field-selector=status.phase!=Running -o json 2>/dev/null || echo '{"items":[]}')
        PROBLEM_POD_COUNT=$(echo "$PROBLEM_PODS" | grep -o '"name":' 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        
        # Get pod counts by phase (default to 0 if commands fail)
        RUNNING_PODS=$(kubectl get pods -A --field-selector=status.phase==Running --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        PENDING_PODS=$(kubectl get pods -A --field-selector=status.phase==Pending --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        FAILED_PODS=$(kubectl get pods -A --field-selector=status.phase==Failed --no-headers 2>/dev/null | wc -l | tr -d ' ' || echo "0")
        
        # Get resource utilization (basic)
        CPU_CAPACITY=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$3} END {print sum}' || echo "N/A")
        MEMORY_CAPACITY=$(kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$5} END {print sum}' || echo "N/A")
        
        # Build JSON output with markers for reliable parsing
        echo "DTE_HEALTHCHECK_JSON_START"
        cat <<EOF
        {
          "timestamp": "$TIMESTAMP",
          "cluster": {
            "name": "%s",
            "region": "%s",
            "provider": "%s",
            "environment": "%s"
          },
          "summary": {
            "status": "healthy",
            "nodeCount": $NODE_COUNT,
            "readyNodes": $READY_NODES,
            "notReadyNodes": $NOTREADY_NODES,
            "podCount": $POD_COUNT,
            "runningPods": $RUNNING_PODS,
            "pendingPods": $PENDING_PODS,
            "failedPods": $FAILED_PODS,
            "problemPodCount": $PROBLEM_POD_COUNT,
            "serviceCount": $SVC_COUNT,
            "namespaceCount": $NS_COUNT,
            "deploymentCount": $DEPLOYMENT_COUNT
          },
          "resources": {
            "cpuUsagePercent": "$CPU_CAPACITY",
            "memoryUsagePercent": "$MEMORY_CAPACITY"
          },
          "details": {
            "nodes": $NODE_STATUS,
            "problematicPods": $PROBLEM_PODS
          }
        }
        EOF
        echo "DTE_HEALTHCHECK_JSON_END"
      volumeMounts:
      - name: kubeconfig
        mountPath: /root/.kube
        readOnly: true
  volumes:
  - name: kubeconfig
    secret:
      secretName: %s-kubeconfig
      optional: true
  entrypoint: health-check`,
		cluster.Name,
		time.Now().Format("20060102-150405"),
		context,
		context,
		cluster.Name,
		cluster.Region,
		cluster.Provider,
		cluster.Environment,
		cluster.Name)
}

func executeArgoWorkflow(ctx context.Context, cluster ClusterInfo, workflowYAML string) (string, error) {
	logger := getActivityLogger(ctx)
	logger.Info("Starting Argo workflow on remote cluster",
		"cluster", cluster.Name)

	// Create K8s client for the target cluster
	clientset, dynamicClient, err := createK8sClient(ctx, cluster, logger)
	if err != nil {
		logger.Error("Failed to create K8s client for remote cluster",
			"target_cluster", cluster.Name,
			"error", err.Error())
		return "", fmt.Errorf("failed to create K8s client for cluster %s: %v", cluster.Name, err)
	}

	// RBAC pre-check: SelfSubjectAccessReview for create workflows in namespace from YAML
	// Extract namespace from YAML to check exact permission
	decoder := yaml.NewDecodingSerializer(unstructured.UnstructuredJSONScheme)
	obj := &unstructured.Unstructured{}
	if _, _, derr := decoder.Decode([]byte(workflowYAML), nil, obj); derr == nil {
		ns := obj.GetNamespace()
		if ns == "" {
			ns = "argo-dte"
		}
		sar := &authv1.SelfSubjectAccessReview{
			Spec: authv1.SelfSubjectAccessReviewSpec{
				ResourceAttributes: &authv1.ResourceAttributes{
					Namespace: ns,
					Verb:      "create",
					Group:     "argoproj.io",
					Resource:  "workflows",
				},
			},
		}
		if resp, err := clientset.AuthorizationV1().SelfSubjectAccessReviews().Create(ctx, sar, metav1.CreateOptions{}); err == nil {
			if !resp.Status.Allowed {
				// Check if the reason mentions GCP IAM permissions
				reason := resp.Status.Reason
				evalError := resp.Status.EvaluationError
				if strings.Contains(reason, "container.thirdPartyObjects.create") || strings.Contains(evalError, "container.thirdPartyObjects.create") {
					logger.Warn("GCP IAM permission denied for creating workflows",
						"target_cluster", cluster.Name,
						"namespace", ns,
						"reason", reason,
						"evaluationError", evalError,
						"note", "GKE requires both Kubernetes RBAC and GCP IAM permission 'container.thirdPartyObjects.create'. Grant the 'Kubernetes Engine Developer' or 'Kubernetes Engine Admin' GCP IAM role to the user or group.")
				} else {
					logger.Warn("RBAC denied for creating workflows",
						"target_cluster", cluster.Name,
						"namespace", ns,
						"reason", reason,
						"evaluationError", evalError)
				}
			} else {
				logger.Info("RBAC allows creating workflows",
					"target_cluster", cluster.Name,
					"namespace", ns)
			}
		} else {
			logger.Warn("Failed to perform RBAC check",
				"target_cluster", cluster.Name,
				"namespace", ns,
				"error", err.Error())
		}
	}

	// Create the workflow using K8s API
	workflowName, err := createWorkflowViaAPI(ctx, dynamicClient, workflowYAML, cluster.Name, logger)
	if err != nil {
		return "", fmt.Errorf("failed to create workflow via API: %v", err)
	}

	logger.Info("Argo workflow created successfully",
		"target_cluster", cluster.Name,
		"workflow_id", workflowName)

	return workflowName, nil
}

func waitForArgoWorkflowCompletion(ctx context.Context, cluster ClusterInfo, workflowID string) (string, bool, error) {
	logger := getActivityLogger(ctx)
	logger.Info("Waiting for Argo workflow completion",
		"target_cluster", cluster.Name,
		"workflow_id", workflowID)

	// Create K8s client for the target cluster
	clientset, dynamicClient, err := createK8sClient(ctx, cluster, logger)
	if err != nil {
		logger.Error("Failed to create K8s client for remote cluster",
			"target_cluster", cluster.Name,
			"error", err.Error())
		return "", false, fmt.Errorf("failed to create K8s client for cluster %s: %v", cluster.Name, err)
	}

	// Poll for workflow completion
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	timeout := time.After(10 * time.Minute) // 10 minute timeout

	for {
		select {
		case <-ctx.Done():
			return "", false, ctx.Err()
		case <-timeout:
			logger.Error("Argo workflow timed out",
				"target_cluster", cluster.Name,
				"workflow_id", workflowID)
			return "", false, fmt.Errorf("workflow %s on cluster %s timed out after 10 minutes", workflowID, cluster.Name)
		case <-ticker.C:
			// Check workflow status using K8s API
			phase, err := getWorkflowStatus(ctx, dynamicClient, workflowID)
			if err != nil {
				logger.Warn("Failed to get workflow status",
					"target_cluster", cluster.Name,
					"workflow_id", workflowID,
					"error", err.Error())
				continue
			}

			logger.Debug("Workflow status check",
				"target_cluster", cluster.Name,
				"phase", phase)

			switch phase {
			case "Succeeded":
				// Get workflow logs/output
				return getWorkflowOutputViaAPI(ctx, clientset, workflowID)
			case "Failed", "Error":
				// Get error details
				message, _ := getWorkflowMessage(ctx, dynamicClient, workflowID)
				logger.Error("Argo workflow failed",
					"target_cluster", cluster.Name,
					"workflow_id", workflowID,
					"error", message)
				return "", false, fmt.Errorf("workflow %s on cluster %s failed: %s", workflowID, cluster.Name, message)
			case "Running", "Pending":
				// Continue waiting
				continue
			default:
				// Unknown phase, continue waiting
				logger.Warn("Unknown workflow phase",
					"target_cluster", cluster.Name,
					"workflow_id", workflowID,
					"phase", phase)
				continue
			}
		}
	}
}

func getWorkflowOutput(ctx context.Context, workflowID string) (string, bool, error) {
	// Get the workflow logs from the main container
	cmd := exec.CommandContext(ctx, "kubectl", "logs", "-l", "workflows.argoproj.io/workflow="+workflowID, "-n", "dtaske", "--tail=100")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", false, fmt.Errorf("failed to get workflow logs: %v", err)
	}

	// Parse the output to extract the kubectl results
	lines := strings.Split(string(output), "\n")
	var results []string

	for _, line := range lines {
		line = strings.TrimSpace(line)
		// Look for lines that look like kubectl service output
		if strings.Contains(line, "ClusterIP") || strings.Contains(line, "LoadBalancer") || strings.Contains(line, "NodePort") {
			results = append(results, line)
		}
	}

	if len(results) == 0 {
		// If no structured output found, return the raw logs
		return string(output), true, nil
	}

	return strings.Join(results, "\n"), true, nil
}

var (
	temporalClient client.Client
	workerInstance worker.Worker
	startupTime    time.Time
	lastTaskTime   time.Time
	jsonLogger     *slog.Logger // JSON logger for structured logging
)

// initJSONLogger initializes the JSON logger
func initJSONLogger() {
	// Use the logger package's custom handler
	jsonLogger = logger.GetLogger()
}

// getWorkflowLogger creates a JSON logger with workflow context information
func getWorkflowLogger(ctx workflow.Context, workflowType string) *slog.Logger {
	return logger.GetWorkflowLogger(ctx, workflowType)
}

// getActivityLogger creates a JSON logger with activity context information
// Activities have access to workflow info through activity.GetInfo
func getActivityLogger(ctx context.Context) *slog.Logger {
	return logger.GetActivityLogger(ctx)
}

func main() {
	startupTime = time.Now()
	lastTaskTime = startupTime

	// Initialize JSON logger
	initJSONLogger()

	jsonLogger.Info("Starting Distributed Task Execution Worker")

	// Initialize Temporal client with logger to avoid "No logger configured" warning
	var err error
	temporalLogger := temporallog.NewStructuredLogger(jsonLogger)
	temporalHostPort := os.Getenv("TEMPORAL_HOSTPORT")
	if temporalHostPort == "" {
		jsonLogger.Error("TEMPORAL_HOSTPORT environment variable is not set")
		os.Exit(1)
	}
	jsonLogger.Info("Connecting to Temporal server", "host_port", temporalHostPort)
	temporalClient, err = client.Dial(client.Options{
		HostPort: temporalHostPort,
		Logger:   temporalLogger,
	})
	if err != nil {
		// Log detailed error information
		jsonLogger.Error("Unable to create Temporal client",
			"error", err.Error(),
			"error_type", fmt.Sprintf("%T", err),
			"host_port", temporalHostPort,
			"namespace", os.Getenv("TEMPORAL_NAMESPACE"))
		os.Exit(1)
	}
	defer temporalClient.Close()

	jsonLogger.Info("Connected to Temporal server",
		"host_port", os.Getenv("TEMPORAL_HOSTPORT"),
		"namespace", os.Getenv("TEMPORAL_NAMESPACE"),
		"task_queue", os.Getenv("TEMPORAL_TASKQUEUE"))

	// Create worker with optimized options for cold start and distributed execution
	workerInstance = worker.New(temporalClient, os.Getenv("TEMPORAL_TASKQUEUE"), worker.Options{
		MaxConcurrentActivityExecutionSize:     20,              // Increased for distributed execution
		MaxConcurrentWorkflowTaskExecutionSize: 20,              // Increased for distributed execution
		MaxConcurrentActivityTaskPollers:       4,               // Multiple pollers for faster task pickup
		MaxConcurrentWorkflowTaskPollers:       4,               // Multiple pollers for faster task pickup
		StickyScheduleToStartTimeout:           5 * time.Second, // Faster sticky execution
	})

	// Register distributed workflows and activities
	// We need to explicitly register them since they're defined in separate files
	workerInstance.RegisterWorkflow(DistributedTaskExecutionWorkflow)
	// HelloWorldWorkflow is deprecated - use DistributedTaskExecutionWorkflow with taskType="hello-world" instead
	// workerInstance.RegisterWorkflow(HelloWorldWorkflow)
	workerInstance.RegisterActivity(ExecuteArgoWorkflowActivity)
	workerInstance.RegisterActivity(FilterServiceDiscoveryResultsActivity)
	workerInstance.RegisterActivity(HealthCheckActivity)
	workerInstance.RegisterActivity(ServiceDiscoveryActivity)
	workerInstance.RegisterActivity(HelloWorldActivity)
	// Deprecated activities (kept for backward compatibility but not used)
	// workerInstance.RegisterActivity(GreetingActivity)
	// workerInstance.RegisterActivity(ProcessingActivity)
	// workerInstance.RegisterActivity(FormattingActivity)

	jsonLogger.Info("Registered workflows",
		"workflows", "DistributedTaskExecutionWorkflow (health-check, service-discovery, hello-world)")
	jsonLogger.Info("Registered activities",
		"activities", []string{
			"ExecuteArgoWorkflowActivity",
			"FilterServiceDiscoveryResultsActivity",
			"HealthCheckActivity",
			"ServiceDiscoveryActivity",
			"HelloWorldActivity",
		})
	jsonLogger.Info("Worker ready to process tasks",
		"task_queue", os.Getenv("TEMPORAL_TASKQUEUE"),
		"supported_workflow_types", "DistributedTaskExecutionWorkflow (health-check, service-discovery, hello-world)")

	// Start worker in background
	go func() {
		jsonLogger.Info("Starting worker")
		if err := workerInstance.Run(worker.InterruptCh()); err != nil {
			jsonLogger.Error("Worker stopped", "error", err.Error())
		}
	}()

	// Set up HTTP routes
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/", infoHandler)
	http.HandleFunc("/worker/status", workerStatusHandler)
	http.HandleFunc("/metrics/taskqueue", taskQueueMetricsHandler)
	// http.HandleFunc("/clusters", clustersHandler) // Commented out until function is added

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	jsonLogger.Info("Server listening",
		"port", port,
		"health_check", fmt.Sprintf("http://localhost:%s/health", port),
		"worker_status", fmt.Sprintf("http://localhost:%s/worker/status", port),
		"task_queue_metrics", fmt.Sprintf("http://localhost:%s/metrics/taskqueue", port))

	// Start HTTP server
	go func() {
		if err := http.ListenAndServe(":"+port, nil); err != nil {
			jsonLogger.Error("Failed to start server", "error", err.Error())
			os.Exit(1)
		}
	}()

	// Wait for shutdown signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	jsonLogger.Info("Shutting down")
	workerInstance.Stop()
	jsonLogger.Info("Worker stopped")
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	uptime := time.Since(startupTime)
	response := HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now(),
		Worker:    "running",
		Uptime:    uptime.String(),
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

func infoHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	response := ServiceInfoResponse{
		Service:   "Distributed Task Execution Worker",
		Version:   "1.0.0",
		Timestamp: time.Now(),
		Endpoints: map[string]string{
			"health":            "/health",
			"worker_status":     "/worker/status",
			"taskqueue_metrics": "/metrics/taskqueue",
		},
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

func workerStatusHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	status := "stopped"
	if workerInstance != nil {
		status = "running"
	}

	uptime := time.Since(startupTime)
	response := map[string]interface{}{
		"worker":         status,
		"taskQueue":      os.Getenv("TEMPORAL_TASKQUEUE"),
		"namespace":      os.Getenv("TEMPORAL_NAMESPACE"),
		"uptime":         uptime.String(),
		"startupTime":    startupTime.Format(time.RFC3339),
		"coldStartReady": uptime > 10*time.Second, // Worker ready after 10 seconds
		"timestamp":      time.Now(),
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

func taskQueueMetricsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// This endpoint provides metrics that Knative autoscaler can use
	// We'll implement proper task queue monitoring for autoscaling

	response := TaskQueueMetricsResponse{
		TaskQueue:         os.Getenv("TEMPORAL_TASKQUEUE"),
		PendingTasks:      0,
		WorkerStatus:      "ready",
		LastTaskProcessed: lastTaskTime,
		Timestamp:         time.Now(),
	}

	// Check if there are actual pending tasks in Temporal
	if workerInstance != nil {
		// For distributed task execution, we want to keep workers available
		// since they handle cross-cluster operations that can be time-sensitive
		// We'll indicate there are always pending tasks to maintain worker availability
		response.PendingTasks = 1
		response.WorkerStatus = "active"
	} else {
		// If worker is not ready yet, indicate pending tasks to trigger scaling
		response.PendingTasks = 1 // Trigger scaling during cold start
		response.WorkerStatus = "cold_starting"
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

// HealthCheckActivity - Activity that performs the actual health check via Argo Workflow
func HealthCheckActivity(ctx context.Context, input map[string]string) (string, error) {
	logger := getActivityLogger(ctx)

	// Extract cluster name and auth tokens from input
	clusterName := input["clusterName"]
	authToken := input["authToken"]
	asapToken := input["asapToken"]
	sctToken := input["sctToken"]
	groups := input["groups"]

	// Log what we received for debugging
	authTokenPreview := ""
	if authToken != "" {
		if len(authToken) > 50 {
			authTokenPreview = authToken[:50] + "..."
		} else {
			authTokenPreview = authToken
		}
	}
	logger.Info("HealthCheckActivity received tokens",
		"cluster", clusterName,
		"has_auth_token", authToken != "",
		"has_asap_token", asapToken != "",
		"has_sct_token", sctToken != "",
		"auth_token_length", len(authToken),
		"asap_token_length", len(asapToken),
		"sct_token_length", len(sctToken),
		"auth_token_preview", authTokenPreview)

	// Validate: if ASAP/SCT tokens are present, authToken (SLAuth token) should not be present
	if (asapToken != "" || sctToken != "") && authToken != "" {
		logger.Warn("Both ASAP/SCT tokens and authToken (SLAuth) are present - ASAP/SCT tokens will be used, authToken will be ignored",
			"cluster", clusterName,
			"has_asap_token", asapToken != "",
			"has_sct_token", sctToken != "",
			"has_auth_token", authToken != "",
			"auth_token_preview", authTokenPreview)
		authToken = "" // Clear it to avoid confusion
	}

	// HF-50: Acquire authEnvMu BEFORE any os.Setenv("DTE_*"). The mutex protects
	// the entire activity-execution window so concurrent activities cannot
	// observe another activity's tokens via os.Getenv() in helpers.go.
	// See auth_env.go for the full bug + fix rationale.
	authEnvMu.Lock()
	defer authEnvMu.Unlock()

	if authToken != "" {
		logger.Info("🔍 HealthCheckActivity started", "cluster", clusterName, "has_auth_token", true)
		// Set SLAuth token in environment for auth provider client
		os.Setenv("DTE_SLAUTH_TOKEN", authToken)
		defer os.Unsetenv("DTE_SLAUTH_TOKEN") // Clean up after activity
	} else if asapToken != "" && sctToken != "" {
		logger.Info("🔍 HealthCheckActivity started", "cluster", clusterName, "has_asap_token", true, "has_sct_token", true)
		// Set ASAP and SCT tokens in environment for auth provider client
		os.Setenv("DTE_ASAP_TOKEN", asapToken)
		os.Setenv("DTE_SCT_TOKEN", sctToken)
		defer func() {
			os.Unsetenv("DTE_ASAP_TOKEN")
			os.Unsetenv("DTE_SCT_TOKEN")
		}()
	} else {
		logger.Info("🔍 HealthCheckActivity started", "cluster", clusterName, "has_auth_token", false, "has_asap_token", asapToken != "", "has_sct_token", sctToken != "")
		logger.Warn("⚠️  No auth token provided - will try to use static token from environment or fallback to gcloud")
	}

	// Set groups in environment if present
	if groups != "" {
		os.Setenv("DTE_GROUPS", groups)
		defer os.Unsetenv("DTE_GROUPS")
		logger.Info("Groups set from X-DTE-GROUPS header", "cluster", clusterName, "groups", groups)
	}

	// 1. Get cluster info from Kibana/cluster registry
	logger.Info("📋 Getting cluster information from registry", "cluster", clusterName)
	cluster, err := GetClusterFromDB(clusterName)
	if err != nil {
		logger.Error("Failed to get cluster information", "cluster", clusterName, "error", err.Error())
		return "", fmt.Errorf("failed to get cluster information for %s: %v", clusterName, err)
	}

	logger.Info("✅ Retrieved cluster information",
		"target_cluster", cluster.Name,
		"full_name", cluster.FullName,
		"region", cluster.Region,
		"project_id", cluster.ProjectID,
		"customer", cluster.Customer)

	// 2. Execute Argo Workflow for health check
	logger.Info("🚀 Executing health check Argo Workflow", "cluster", clusterName)
	activity.RecordHeartbeat(ctx, "Executing Argo Workflow...")

	argoResult, err := ExecuteArgoWorkflowActivity(ctx, *cluster, "health-check")
	if err != nil {
		logger.Error("Failed to execute Argo Workflow", "cluster", clusterName, "error", err.Error())
		return "", fmt.Errorf("failed to execute health check workflow: %v", err)
	}

	if !argoResult.Success {
		logger.Error("Health check workflow failed", "cluster", clusterName, "error", argoResult.Error)
		return "", fmt.Errorf("health check workflow failed: %s", argoResult.Error)
	}

	logger.Info("✅ HealthCheckActivity completed successfully",
		"target_cluster", clusterName,
		"output_length", len(argoResult.Output))

	// Return the full output from the Argo Workflow with markers preserved
	// The markers help the parser reliably extract the JSON even after encoding
	result := fmt.Sprintf("Health check completed for cluster %s\n\nArgo Workflow ID: %s\n\nDTE_HEALTHCHECK_JSON_START\n%s\nDTE_HEALTHCHECK_JSON_END",
		clusterName, argoResult.WorkflowID, argoResult.Output)

	return result, nil
}

// ServiceDiscoveryActivity - Activity that performs service discovery
func ServiceDiscoveryActivity(ctx context.Context, input map[string]string) (string, error) {
	logger := getActivityLogger(ctx)

	// Extract cluster name and auth tokens from input
	clusterName := input["clusterName"]
	authToken := input["authToken"]
	asapToken := input["asapToken"]
	sctToken := input["sctToken"]
	groups := input["groups"]

	// Validate: if ASAP/SCT tokens are present, authToken (SLAuth token) should not be present
	if (asapToken != "" || sctToken != "") && authToken != "" {
		logger.Warn("Both ASAP/SCT tokens and authToken (SLAuth) are present - ASAP/SCT tokens will be used, authToken will be ignored",
			"cluster", clusterName,
			"has_asap_token", asapToken != "",
			"has_sct_token", sctToken != "",
			"has_auth_token", authToken != "")
		authToken = "" // Clear it to avoid confusion
	}

	// HF-50: Acquire authEnvMu BEFORE any os.Setenv("DTE_*"). See HealthCheckActivity
	// above (and auth_env.go) for full rationale.
	authEnvMu.Lock()
	defer authEnvMu.Unlock()

	if authToken != "" {
		logger.Info("🔍 ServiceDiscoveryActivity started", "cluster", clusterName, "has_auth_token", true)
		// Set SLAuth token in environment for auth provider client
		os.Setenv("DTE_SLAUTH_TOKEN", authToken)
		defer os.Unsetenv("DTE_SLAUTH_TOKEN") // Clean up after activity
	} else if asapToken != "" && sctToken != "" {
		logger.Info("🔍 ServiceDiscoveryActivity started", "cluster", clusterName, "has_asap_token", true, "has_sct_token", true)
		// Set ASAP and SCT tokens in environment for auth provider client
		os.Setenv("DTE_ASAP_TOKEN", asapToken)
		os.Setenv("DTE_SCT_TOKEN", sctToken)
		defer func() {
			os.Unsetenv("DTE_ASAP_TOKEN")
			os.Unsetenv("DTE_SCT_TOKEN")
		}()
	} else {
		logger.Info("🔍 ServiceDiscoveryActivity started", "cluster", clusterName, "has_auth_token", false, "has_asap_token", asapToken != "", "has_sct_token", sctToken != "")
		logger.Warn("⚠️  No auth token provided - will try to use static token from environment or fallback to gcloud")
	}

	// Set groups in environment if present
	if groups != "" {
		os.Setenv("DTE_GROUPS", groups)
		defer os.Unsetenv("DTE_GROUPS")
		logger.Info("Groups set from X-DTE-GROUPS header", "cluster", clusterName, "groups", groups)
	}

	// 1. Get cluster info from Kibana/cluster registry
	logger.Info("📋 Getting cluster information from registry", "cluster", clusterName)
	cluster, err := GetClusterFromDB(clusterName)
	if err != nil {
		logger.Error("Failed to get cluster information", "cluster", clusterName, "error", err.Error())
		return "", fmt.Errorf("failed to get cluster information for %s: %v", clusterName, err)
	}

	logger.Info("✅ Retrieved cluster information",
		"target_cluster", cluster.Name,
		"full_name", cluster.FullName,
		"region", cluster.Region,
		"project_id", cluster.ProjectID,
		"customer", cluster.Customer)

	// 2. Execute Argo Workflow for service discovery
	logger.Info("🚀 Executing service discovery Argo Workflow", "cluster", clusterName)
	activity.RecordHeartbeat(ctx, "Executing Argo Workflow...")

	argoResult, err := ExecuteArgoWorkflowActivity(ctx, *cluster, "service-discovery")
	if err != nil {
		logger.Error("Failed to execute Argo Workflow", "cluster", clusterName, "error", err.Error())
		return "", fmt.Errorf("failed to execute service discovery workflow: %v", err)
	}

	if !argoResult.Success {
		logger.Error("Service discovery workflow failed", "cluster", clusterName, "error", argoResult.Error)
		return "", fmt.Errorf("service discovery workflow failed: %s", argoResult.Error)
	}

	logger.Info("✅ ServiceDiscoveryActivity completed successfully",
		"target_cluster", clusterName,
		"output_length", len(argoResult.Output))

	// Return the full output from the Argo Workflow
	result := fmt.Sprintf("Service discovery completed for cluster %s\n\nArgo Workflow ID: %s\n\nResults:\n%s",
		clusterName, argoResult.WorkflowID, argoResult.Output)

	return result, nil
}

// HelloWorldActivity - Activity that prints "Hello world <cluster name>" without invoking Argo workflows
func HelloWorldActivity(ctx context.Context, input map[string]string) (string, error) {
	logger := getActivityLogger(ctx)

	// Extract cluster name from input
	clusterName := input["clusterName"]

	logger.Info("HelloWorldActivity started", "cluster", clusterName)

	// Simply return a hello world message with the cluster name
	result := fmt.Sprintf("Hello world %s", clusterName)

	logger.Info("HelloWorldActivity completed successfully",
		"target_cluster", clusterName,
		"result", result)

	return result, nil
}

// HelloWorldWorkflow - Simple hello world workflow that accepts a name parameter
// DEPRECATED: Use DistributedTaskExecutionWorkflow with taskType="hello-world" instead
func HelloWorldWorkflow(ctx workflow.Context, name string) (string, error) {
	logger := getWorkflowLogger(ctx, "HelloWorldWorkflow")
	logger.Info("HelloWorldWorkflow started", "name", name)

	// Set workflow timeout with retries
	ctx = workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
		StartToCloseTimeout:    30 * time.Second,
		ScheduleToCloseTimeout: 60 * time.Second,
		RetryPolicy: &temporal.RetryPolicy{
			InitialInterval:        time.Second,
			BackoffCoefficient:     2.0,
			MaximumInterval:        30 * time.Second,
			MaximumAttempts:        5,
			NonRetryableErrorTypes: []string{},
		},
	})

	// Execute the greeting activity
	var greeting string
	err := workflow.ExecuteActivity(ctx, GreetingActivity, name).Get(ctx, &greeting)
	if err != nil {
		logger.Error("GreetingActivity failed", "error", err.Error())
		return "", err
	}

	// Execute processing activity
	err = workflow.ExecuteActivity(ctx, ProcessingActivity, greeting).Get(ctx, &greeting)
	if err != nil {
		logger.Error("ProcessingActivity failed", "error", err.Error())
		return "", err
	}

	// Add a small delay to simulate workflow logic
	err = workflow.Sleep(ctx, 2*time.Second)
	if err != nil {
		logger.Error("Workflow sleep failed", "error", err.Error())
		return "", err
	}

	// Execute final formatting activity
	var result string
	err = workflow.ExecuteActivity(ctx, FormattingActivity, greeting).Get(ctx, &result)
	if err != nil {
		logger.Error("FormattingActivity failed", "error", err.Error())
		return "", err
	}

	logger.Info("HelloWorldWorkflow completed successfully", "result", result)
	return result, nil
}

// GreetingActivity creates a personalized greeting
func GreetingActivity(ctx context.Context, name string) (string, error) {
	logger := getActivityLogger(ctx)
	logger.Info("GreetingActivity started", "name", name)

	// Simulate some processing time
	time.Sleep(1 * time.Second)

	greeting := fmt.Sprintf("Hello, %s!", name)
	logger.Info("GreetingActivity completed", "greeting", greeting)

	return greeting, nil
}

// ProcessingActivity processes the greeting and adds context
func ProcessingActivity(ctx context.Context, greeting string) (string, error) {
	logger := getActivityLogger(ctx)
	logger.Info("ProcessingActivity started", "input", greeting)

	// Simulate some processing time
	time.Sleep(500 * time.Millisecond)

	// Add context to the greeting
	processed := fmt.Sprintf("%s Welcome to Temporal!", greeting)
	logger.Info("ProcessingActivity completed", "output", processed)

	return processed, nil
}

// FormattingActivity formats the final result
func FormattingActivity(ctx context.Context, message string) (string, error) {
	logger := getActivityLogger(ctx)
	logger.Info("FormattingActivity started", "input", message)

	// Simulate some formatting time
	time.Sleep(300 * time.Millisecond)

	// Add final formatting
	formatted := fmt.Sprintf("🎉 %s 🎉", message)
	logger.Info("FormattingActivity completed", "output", formatted)

	return formatted, nil
}
