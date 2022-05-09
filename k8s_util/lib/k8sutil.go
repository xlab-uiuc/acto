package main

import "C"
import (
	"fmt"

	"k8s.io/apimachinery/pkg/api/resource"
)

//export parse
func parse(valuePtr *C.char) *C.char {
	value := C.GoString(valuePtr)
	q := resource.Quantity{Format: resource.DecimalSI}
	q.UnmarshalJSON([]byte(value))
	return C.CString(q.String())
}

func main() {
	fmt.Println("Hello, world.")
}
