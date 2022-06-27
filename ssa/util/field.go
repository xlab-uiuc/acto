package util

import (
	"bytes"
	"fmt"
	"go/types"
)

type IndexField []int

type Field struct {
	Path []string
}

func (f *Field) Equal(v Field) bool {
	if len(f.Path) != len(v.Path) {
		return false
	}

	for i := 0; i < len(f.Path); i++ {
		if f.Path[i] != v.Path[i] {
			return false
		}
	}
	return true
}

func (f *Field) Clone() *Field {
	newPath := make([]string, len(f.Path))
	copy(newPath, f.Path)

	return &Field{
		Path: newPath,
	}
}

func (f *Field) String() string {
	return fmt.Sprint(f.Path)
}

func NewSubField(parentStruct *types.Struct, parentField Field, fieldIndex int) *Field {
	newPath := make([]string, len(parentField.Path))
	copy(newPath, parentField.Path)

	tag := parentStruct.Tag(fieldIndex)
	newPath = append(newPath, GetFieldNameFromJsonTag(tag))
	return &Field{
		Path: newPath,
	}
}

func NewIndexField(parentField Field) *Field {
	newPath := make([]string, len(parentField.Path))
	copy(newPath, parentField.Path)

	newPath = append(newPath, "INDEX")
	return &Field{
		Path: newPath,
	}
}

type FieldSet struct {
	fields []Field
}

func NewFieldSet() *FieldSet {
	return &FieldSet{
		fields: make([]Field, 0),
	}
}

func (fs *FieldSet) Add(f *Field) bool {
	if fs.Contain(*f) {
		return false
	}
	fs.fields = append(fs.fields, *f)
	return true
}

func (fs *FieldSet) Delete(f *Field) {
	newFields := []Field{}
	for _, field := range fs.fields {
		if !field.Equal(*f) {
			newFields = append(newFields, field)
		}
	}
	fs.fields = newFields
}

func (fs *FieldSet) Contain(f Field) bool {
	for _, field := range fs.fields {
		if field.Equal(f) {
			return true
		}
	}
	return false
}

func (fs FieldSet) Fields() []Field {
	return fs.fields
}

func (fs FieldSet) IsMetadata() bool {
	if len(fs.fields) == 1 {
		if fs.fields[0].Equal(Field{Path: []string{"root", "metadata"}}) {
			return true
		}
	}
	return false
}

func (fs FieldSet) IsStatus() bool {
	if len(fs.fields) == 1 {
		if fs.fields[0].Equal(Field{Path: []string{"root", "status"}}) {
			return true
		}
	}
	return false
}

func (fs FieldSet) IsTypeMeta() bool {
	if len(fs.fields) == 1 {
		if fs.fields[0].Equal(Field{Path: []string{"root", ""}}) {
			return true
		}
	}
	return false
}

func (fs FieldSet) String() string {
	var buf bytes.Buffer
	buf.WriteString("[")
	for _, field := range fs.fields {
		buf.WriteString(field.String())
	}
	buf.WriteString("]")
	return buf.String()
}

func MergeFieldSets(sets ...FieldSet) *FieldSet {
	ret := NewFieldSet()
	for _, set := range sets {
		for _, field := range set.Fields() {
			ret.Add(&field)
		}
	}
	return ret
}
