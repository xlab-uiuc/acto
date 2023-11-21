package main

import (
	"flag"
	"os"
	"path/filepath"

	"github.com/goki/ki/ki"
	fieldcount "github.com/xlab-uiuc/acto/scripts/fieldCount"
	"gopkg.in/yaml.v3"
)

func main() {
	projectPath := flag.String("path", "/home/tyler/acto-ops/percona-server-mongodb-operator/e2e-tests", "the path to the operator's source dir")
	flag.Parse()

	files, err := filepath.Glob(filepath.Join(*projectPath, "*/compare/*.yml"))
	if err != nil {
		panic(err)
	}

	root := fieldcount.FieldNode{}
	root.InitName(&root, "root")
	fieldSet := make(fieldcount.StringSet)

	for _, file := range files {
		println(file)
		data, err := os.ReadFile(file)
		if err != nil {
			panic(err)
		}

		var instance map[string]interface{}
		err = yaml.Unmarshal(data, &instance)
		if err != nil {
			panic(err)
		}

		var kind string
		switch instance["kind"].(type) {
		case string:
			kind = instance["kind"].(string)
		default:
			continue
		}

		var kindNode ki.Ki
		if kindNode = root.ChildByName(kind, 0); kindNode == nil {
			kindNode = &fieldcount.FieldNode{Used: false}
			kindNode.InitName(kindNode, kind)
			root.AddChild(kindNode)
		}

		fieldcount.MapToTree(instance, kindNode)
	}

	root.FuncDownBreadthFirst(0, fieldSet, func(k ki.Ki, level int, d interface{}) bool {
		m := d.(fieldcount.StringSet)
		if fieldNode, ok := k.(*fieldcount.FieldNode); ok {
			m[fieldNode.Path()] = struct{}{}
		}
		return true
	})

	println(len(fieldSet))
}
