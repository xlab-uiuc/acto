package analysis

import (
	"encoding/csv"
	"encoding/json"
	"go/token"
	"log"
	"os"
	"sort"
	"strings"

	"golang.org/x/tools/go/ssa"
)

func FindAllUses(context *Context) {
	fieldToValueMap := context.FieldToValueMap

	file, err := os.Create("uses.csv")
	if err != nil {
		log.Fatal(err)
	}
	csvWriter := csv.NewWriter(file)

	for field, valueSlice := range fieldToValueMap {
		fieldSlice := []string{}
		err := json.Unmarshal([]byte(field), &fieldSlice)
		if err != nil {
			log.Fatal(err)
		}
		fieldString := strings.Join(fieldSlice, ".")
		for _, value := range *valueSlice {
			position := context.Program.Fset.Position(value.Pos())
			if position.IsValid() {
				f, err := os.ReadFile(position.Filename)
				if err != nil {
					log.Fatal(err)
				}
				line := string(f[position.Offset-position.Column+1 : position.Offset])

				for i := position.Offset; string(f[i]) != "\n"; i++ {
					line += string(f[i])
				}

				csvWriter.Write([]string{fieldString, position.String(), line})
			}

		}
	}
}

func FindUsesInConditions(context *Context, frontierSet map[ssa.Value]bool) {
	branches := map[*ssa.If]PropogatedValue{}
	for value, _ := range frontierSet {
		newBranches := PropogateToConditions(context, value)
		for branch, propagatedValue := range newBranches {
			branches[branch] = propagatedValue
		}
	}

	branchesByPos := map[string]PropogatedValue{}
	posSlice := []token.Pos{}
	for branch, propogatedValue := range branches {
		branchesByPos[context.Program.Fset.Position(branch.Cond.Pos()).String()] = propogatedValue
		posSlice = append(posSlice, branch.Cond.Pos())
	}

	sort.Slice(posSlice, func(i, j int) bool {
		return posSlice[i] < posSlice[j]
	})

	file, err := os.Create("branches.csv")
	if err != nil {
		log.Fatal(err)
	}
	csvWriter := csv.NewWriter(file)
	for _, pos := range posSlice {
		position := context.Program.Fset.Position(pos)
		if position.IsValid() {
			f, err := os.ReadFile(position.Filename)
			if err != nil {
				log.Fatal(err)
			}
			line := string(f[position.Offset-position.Column+1 : position.Offset])

			for i := position.Offset; string(f[i]) != "\n"; i++ {
				line += string(f[i])
			}

			csvWriter.Write([]string{position.String(), line})
		}
	}
	csvWriter.Flush()
}

func PropogateToConditions(context *Context, source ssa.Value) (branches map[*ssa.If]PropogatedValue) {
	worklist := []PropogatedValue{{
		Value:  source,
		Path:   []ssa.Value{},
		Source: source,
	}}

	phiMap := make(map[ssa.Value]bool)

	branches = map[*ssa.If]PropogatedValue{}

	for len(worklist) > 0 {
		workitem := worklist[len(worklist)-1]
		worklist = worklist[:len(worklist)-1]

		referrers := workitem.Value.Referrers()
		for _, referrer := range *referrers {
			switch typedInst := referrer.(type) {
			case ssa.Value:
				switch typedValue := typedInst.(type) {
				case *ssa.BinOp:
					newPath := append([]ssa.Value{}, workitem.Path...)
					newPropogatedValue := PropogatedValue{
						Value:  typedValue,
						Path:   append(newPath, workitem.Value),
						Source: workitem.Source,
					}
					worklist = append(worklist, newPropogatedValue)
				case *ssa.Call:
					newPath := append([]ssa.Value{}, workitem.Path...)
					newPropogatedValue := PropogatedValue{
						Value:  typedValue,
						Path:   append(newPath, workitem.Value),
						Source: workitem.Source,
					}
					worklist = append(worklist, newPropogatedValue)
				case *ssa.ChangeInterface:
					newPath := append([]ssa.Value{}, workitem.Path...)
					newPropogatedValue := PropogatedValue{
						Value:  typedValue,
						Path:   append(newPath, workitem.Value),
						Source: workitem.Source,
					}
					worklist = append(worklist, newPropogatedValue)
				case *ssa.ChangeType:
					newPath := append([]ssa.Value{}, workitem.Path...)
					newPropogatedValue := PropogatedValue{
						Value:  typedValue,
						Path:   append(newPath, workitem.Value),
						Source: workitem.Source,
					}
					worklist = append(worklist, newPropogatedValue)
				case *ssa.Convert:
					newPath := append([]ssa.Value{}, workitem.Path...)
					newPropogatedValue := PropogatedValue{
						Value:  typedValue,
						Path:   append(newPath, workitem.Value),
						Source: workitem.Source,
					}
					worklist = append(worklist, newPropogatedValue)
				case *ssa.MakeInterface:
					newPath := append([]ssa.Value{}, workitem.Path...)
					newPropogatedValue := PropogatedValue{
						Value:  typedValue,
						Path:   append(newPath, workitem.Value),
						Source: workitem.Source,
					}
					worklist = append(worklist, newPropogatedValue)
				case *ssa.Phi:
					if _, ok := phiMap[typedValue]; !ok {
						phiMap[typedValue] = true
						newPath := append([]ssa.Value{}, workitem.Path...)
						newPropogatedValue := PropogatedValue{
							Value:  typedValue,
							Path:   append(newPath, workitem.Value),
							Source: workitem.Source,
						}
						worklist = append(worklist, newPropogatedValue)
					}
				case *ssa.UnOp:
					newPath := append([]ssa.Value{}, workitem.Path...)
					newPropogatedValue := PropogatedValue{
						Value:  typedValue,
						Path:   append(newPath, workitem.Value),
						Source: workitem.Source,
					}
					worklist = append(worklist, newPropogatedValue)
				}
			case *ssa.If:
				branches[typedInst] = workitem
			}
		}
	}
	return
}

type DataPath []ssa.Value

type PropogatedValue struct {
	Source ssa.Value
	Path   DataPath
	Value  ssa.Value
}
