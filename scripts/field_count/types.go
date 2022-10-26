package fieldcount

import (
	"bytes"
	"sort"
)

type StringSet map[string]struct{}

func (s StringSet) String() string {
	var b bytes.Buffer
	for k := range s {
		b.WriteString(k)
		b.WriteString("\n")
	}
	return b.String()
}

func (s StringSet) Slice() []string {
	var slice []string
	for k := range s {
		slice = append(slice, k)
	}
	sort.Strings(slice)
	return slice
}

func (s StringSet) DeepCopy() StringSet {
	result := make(StringSet)
	for k := range s {
		result[k] = struct{}{}
	}
	return result
}

type Entry interface{}
