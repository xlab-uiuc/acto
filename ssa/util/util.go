package util

import (
	"strconv"
	"strings"

	"golang.org/x/tools/go/ssa"
)

func AddFieldToValueFieldSetMap(m map[ssa.Value]*FieldSet, v ssa.Value, f *Field) bool {
	if fieldSet, ok := m[v]; ok {
		// this typedValue already exists in the map, try add the field to the set
		if ok := fieldSet.Add(f); ok {
			// this field not yet exists in the set yet, successfully added
			return true
		} else {
			// value already exists in map, and path already exists in the path set
			return false
		}
	} else {
		// this typedValue not yet exists in the map, create a FieldSet for it
		m[v] = NewFieldSet()
		m[v].Add(f)
		return true
	}
}

func MergeMaps(m1 map[ssa.Value]*FieldSet, m2 map[ssa.Value]*FieldSet) {
	for k, v := range m2 {
		m1[k] = v
	}
}

func GetFieldNameFromJsonTag(tag string) string {
	jsonTag, _ := tagLookUp(tag, "json")
	v := strings.Split(jsonTag, ",")[0]
	return v
}

func tagLookUp(tag string, key string) (string, bool) {
	for tag != "" {
		// Skip leading space.
		i := 0
		for i < len(tag) && tag[i] == ' ' {
			i++
		}
		tag = tag[i:]
		if tag == "" {
			break
		}

		// Scan to colon. A space, a quote or a control character is a syntax error.
		// Strictly speaking, control chars include the range [0x7f, 0x9f], not just
		// [0x00, 0x1f], but in practice, we ignore the multi-byte control characters
		// as it is simpler to inspect the tag's bytes than the tag's runes.
		i = 0
		for i < len(tag) && tag[i] > ' ' && tag[i] != ':' && tag[i] != '"' && tag[i] != 0x7f {
			i++
		}
		if i == 0 || i+1 >= len(tag) || tag[i] != ':' || tag[i+1] != '"' {
			break
		}
		name := string(tag[:i])
		tag = tag[i+1:]

		// Scan quoted string to find value.
		i = 1
		for i < len(tag) && tag[i] != '"' {
			if tag[i] == '\\' {
				i++
			}
			i++
		}
		if i >= len(tag) {
			break
		}
		qvalue := string(tag[:i+1])
		tag = tag[i+1:]

		if key == name {
			value, err := strconv.Unquote(qvalue)
			if err != nil {
				break
			}
			return value, true
		}
	}
	return "", false
}
