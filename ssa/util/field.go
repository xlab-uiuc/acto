package util

import (
	"fmt"
	"go/types"
)

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

func NewSubField(parentStruct *types.Struct, parentField Field, fieldIndex int) *Field {
	newPath := make([]string, len(parentField.Path))
	copy(newPath, parentField.Path)

	tag := parentStruct.Tag(fieldIndex)
	newPath = append(newPath, GetFieldNameFromJsonTag(tag))
	fmt.Printf("%s -> %s\n", parentField.Path, newPath)
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
