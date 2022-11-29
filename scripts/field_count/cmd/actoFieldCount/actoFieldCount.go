package main

import (
	"flag"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	fieldcount "github.com/xlab-uiuc/acto/scripts/fieldCount"
)

func main() {
	yamlDir := flag.String("testrun", "", "the path to the config file")
	seedType := flag.String("type", "", "the name of the operator")
	flag.Parse()

	fieldSet := make(fieldcount.StringSet)

	if *yamlDir != "" {
		filepath.WalkDir(*yamlDir, fs.WalkDirFunc(func(path string, d os.DirEntry, err error) error {
			if strings.HasSuffix(path, ".yaml") || strings.HasSuffix(path, ".yml") {
				fieldcount.CountFieldYaml(path, fieldSet, *seedType)
			}
			return nil
		}))
	} else {
		flag.Usage()
	}
	print(fieldSet.String())
	print(len(fieldSet))
}
