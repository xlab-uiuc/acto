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

type ConfigFile map[string]Config

type Config struct {
	ProjectPath  string     `json:"projectPath"`
	YamlDir      string     `json:"yamlDir"`
	TestDir      string     `json:"testDir"`
	SeedType     string     `json:"seedType"`
	SeedPkgPath  string     `json:"seedPkgPath"`
	TestPlanPath string     `json:"testPlanPath"`
	PrunedFields [][]string `json:"prunedFields"`
}

func main() {
	configPath := flag.String("config", "config.json", "the path to the config file")
	operatorName := flag.String("operator", "zookeeper-operator", "the name of the operator")
	flag.Parse()

	// Configure the global logger
	os.Remove("debug.log")
	cfg := zap.NewDevelopmentConfig()
	cfg.OutputPaths = []string{"debug.log"}
	logger, _ := cfg.Build()
	defer logger.Sync() // flushes buffer, if any
	zap.ReplaceGlobals(logger)

	configFileData, err := os.ReadFile(*configPath)
	if err != nil {
		panic(err)
	}
	var configFile ConfigFile
	err = json.Unmarshal(configFileData, &configFile)
	if err != nil {
		panic(err)
	}
	config := configFile[*operatorName]
	projectPath := &config.ProjectPath
	yamlDir := &config.YamlDir
	testDir := &config.TestDir
	seedType := &config.SeedType
	seedPkgPath := &config.SeedPkgPath
	testPlanPath := &config.TestPlanPath
	prunedFields := config.PrunedFields

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
			if field != "" {
				path += "/" + field
			}
		}
		testPlanFieldSet[path] = struct{}{}
	}

	fieldSet := fieldCount.CountField(projectPath, testDir, seedType, seedPkgPath)
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

	operatorTestFieldsAfterPrune := fieldSet.DeepCopy()
	for _, prunedField := range prunedFields {
		field := "/root"
		for _, f := range prunedField {
			field += "/" + f
		}
		for f := range fieldSet {
			if strings.HasPrefix(f, field) && f != field {
				delete(operatorTestFieldsAfterPrune, f)
			}
		}
	}

	compareResult := Result{
		NumActoFields:                   len(testPlanFieldSet),
		NumOperatorTestFields:           len(fieldSet),
		NumOperatorTestFieldsAfterPrune: len(operatorTestFieldsAfterPrune),
		ActoFields:                      testPlanFieldSet.Slice(),
		OperatorTestFields:              fieldSet.Slice(),
		OperatorTestFieldsAfterPrune:    operatorTestFieldsAfterPrune.Slice(),
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
	NumActoFields                   int      `json:"num_acto_fields"`
	NumOperatorTestFields           int      `json:"num_operator_test_fields"`
	NumOperatorTestFieldsAfterPrune int      `json:"num_operator_test_fields_after_prune"`
	ActoFields                      []string `json:"acto_fields"`
	OperatorTestFields              []string `json:"operator_test_fields"`
	OperatorTestFieldsAfterPrune    []string `json:"operator_test_fields_after_prune"`
}
