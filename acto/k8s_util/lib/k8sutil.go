package main

import "C"
import (
	"fmt"

	"gopkg.in/inf.v0"
	"k8s.io/apimachinery/pkg/api/resource"
)

//export parse
func parse(valuePtr *C.char) *C.char {
	value := C.GoString(valuePtr)
	q, err := resource.ParseQuantity(value)
	if err != nil {
		return C.CString("INVALID")
	}
	// return C.CString(strconv.FormatInt(q.Value(), 10))
	const milliScale = -3
	q.RoundUp(milliScale) // round up to the nearest milli for V1Api compatiability

	return C.CString(q.AsDec().String())
}

//export doubleIt
func doubleIt(valuePtr *C.char) *C.char {
	value := C.GoString(valuePtr)
	q, err := resource.ParseQuantity(value)
	if err != nil {
		return C.CString("INVALID")
	}

	q.Add(q)
	return C.CString(q.String())
}

//export halfIt
func halfIt(valuePtr *C.char) *C.char {
	value := C.GoString(valuePtr)
	q, err := resource.ParseQuantity(value)
	if err != nil {
		return C.CString("INVALID")
	}

	halfDec := inf.NewDec(5, 1)
	result := q.AsDec().Mul(q.AsDec(), halfDec)
	return C.CString(result.String())
}

func main() {
	// fmt.Println("Hello, world.")
	test := "-92743e6047801799"
	ans, err := resource.ParseQuantity(test)
	if err != nil {
		fmt.Printf("Error in converting the string %v", err)
	}
	fmt.Print(ans.RoundUp(-3))
	fmt.Printf("The value is %v", ans)
}
