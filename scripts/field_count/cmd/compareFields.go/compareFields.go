package main

import (
	"encoding/json"
	"flag"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	fieldCount "github.com/xlab-uiuc/acto/scripts/fieldCount"
	"go.uber.org/zap"
)

func main() {
	projectPath := flag.String("project-path", "/home/tyler/zookeeper-operator", "the path to the operator's source dir")
	yamlDir := flag.String("yaml-dir", "", "the path to the operator's system test yaml dir")
	seedType := flag.String("seed-type", "ZookeeperCluster", "The type of the root")
	seedPkgPath := flag.String("seed-pkg", "github.com/pravega/zookeeper-operator/api/v1beta1", "The package path of the root")
	testPlanPath := flag.String("test-plan", "", "The path to the test plan")
	flag.Parse()

	// Configure the global logger
	os.Remove("debug.log")
	cfg := zap.NewDevelopmentConfig()
	cfg.OutputPaths = []string{"debug.log"}
	logger, _ := cfg.Build()
	defer logger.Sync() // flushes buffer, if any
	zap.ReplaceGlobals(logger)

	data, err := os.ReadFile(*testPlanPath)
	if err != nil {
		panic(err)
	}
	var result map[string]interface{}

	json.Unmarshal(data, &result)
	sLogger := zap.S()

	testPlanFieldSet := make(fieldCount.StringSet)
	for pathStr, _ := range result {
		pathSlice := []string{}
		json.Unmarshal([]byte(pathStr), &pathSlice)

		path := "/root"
		for _, field := range pathSlice {
			path += "/" + field
		}
		testPlanFieldSet[path] = struct{}{}
	}

	fieldSet := fieldCount.CountField(projectPath, seedType, seedPkgPath)
	sLogger.Infof("Test Plan Fields:\n%s\n", Intersect(testPlanFieldSet, fieldSet).String())

	if *yamlDir != "" {
		filepath.WalkDir(*yamlDir, fs.WalkDirFunc(func(path string, d os.DirEntry, err error) error {
			if strings.HasSuffix(path, ".yaml") || strings.HasSuffix(path, ".yml") {
				fieldCount.CountFieldYaml(path, fieldSet, *seedType)
			}
			return nil
		}))
	}

	actoExtra := make(fieldCount.StringSet)
	for field := range testPlanFieldSet {
		if _, ok := fieldSet[field]; !ok {
			actoExtra[field] = struct{}{}
		}
	}
	sLogger.Infof("Acto Test Extra Fields:\n%s\n", actoExtra)

	compareResult := Result{
		NumActoFields:         len(testPlanFieldSet),
		NumOperatorTestFields: len(fieldSet),
		ActoFields:            testPlanFieldSet.Slice(),
		OperatorTestFields:    fieldSet.Slice(),
	}

	data, err = json.MarshalIndent(compareResult, "", "  ")
	if err != nil {
		panic(err)
	}
	os.WriteFile("compareResult.json", data, 0644)
}

func Intersect(a, b fieldCount.StringSet) fieldCount.StringSet {
	result := make(fieldCount.StringSet)
	for k := range a {
		if _, ok := b[k]; ok {
			result[k] = struct{}{}
		}
	}
	return result
}

type Result struct {
	NumActoFields         int      `json:"num_acto_fields"`
	NumOperatorTestFields int      `json:"num_operator_test_fields"`
	ActoFields            []string `json:"acto_fields"`
	OperatorTestFields    []string `json:"operator_test_fields"`
}
