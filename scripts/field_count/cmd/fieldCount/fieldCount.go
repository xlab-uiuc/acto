package main

import (
	"flag"
	"os"

	fieldCount "github.com/xlab-uiuc/acto/scripts/fieldCount"
	"go.uber.org/zap"
)

func main() {
	projectPath := flag.String("project-path", "/home/tyler/zookeeper-operator", "the path to the operator's source dir")
	seedType := flag.String("seed-type", "ZookeeperCluster", "The type of the root")
	seedPkgPath := flag.String("seed-pkg", "github.com/pravega/zookeeper-operator/api/v1beta1", "The package path of the root")
	testDir := flag.String("test-dir", "", "the path to the operator's system test dir")
	flag.Parse()

	// Configure the global logger
	os.Remove("debug.log")
	cfg := zap.NewDevelopmentConfig()
	cfg.OutputPaths = []string{"debug.log"}
	logger, _ := cfg.Build()
	defer logger.Sync() // flushes buffer, if any
	zap.ReplaceGlobals(logger)

	fieldCount.CountField(projectPath, testDir, seedType, seedPkgPath)
}
