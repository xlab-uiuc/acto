package main

import "C"
import (
	"fmt"
	"strconv"

	"k8s.io/apimachinery/pkg/api/resource"
)

//export parse
func parse(valuePtr *C.char) *C.char {
	value := C.GoString(valuePtr)
	q, err := resource.ParseQuantity(value)
	if err != nil {
		return C.CString(value)
	}
	return C.CString(strconv.FormatInt(q.Value(), 10))
}

func main() {
	fmt.Println("Hello, world.")
}
