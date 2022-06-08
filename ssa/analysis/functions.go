package analysis

import (
	"fmt"
	"go/types"
	"log"

	"golang.org/x/tools/go/ssa"
)

func IsStaticFunctionSink(function *ssa.Function) bool {
	log.Printf("Is static function %s sink?\n", function.String())
	if function.Pkg != nil && PackageSinks[function.Pkg.Pkg.Name()] {
		return true
	}

	if StaticFunctionSinks[function.String()] {
		log.Printf("static function %s is sink\n", function.String())
		return true
	}
	return false
}

func IsInterfaceFunctionSink(function *types.Func) bool {
	log.Printf("%s is interface function sink??\n", function.FullName())
	if function.Pkg() != nil && function.Pkg().Name() == "reflect" {
		log.Printf("%s is interface function sink\n", function.Id())
		return true
	}

	if _, ok := InterfaceFunctionSinks[function.FullName()]; ok {
		log.Printf("interface function %s is sink\n", function.FullName())
		return true
	}
	return false
}

func IsK8sInterfaceFunction(function *types.Func) bool {
	if _, ok := K8sInterfaceFunctions[function.FullName()]; ok {
		return true
	}
	return false
}

func IsK8sStaticFunction(function *ssa.Function) bool {
	if _, ok := K8sStaticFunctions[function.String()]; ok {
		return true
	}
	return false
}

func GetKnownInterfaceFunction(function *types.Func, callSiteTaintedParamIndexSet []int) *FunctionTaintResult {
	if knownFunctionResult, ok := KnownInterfaceFunctionWithoutParam[function.FullName()]; ok {
		log.Printf("[%s] is a known interface function\n", function.FullName())
		return &knownFunctionResult
	}

	functionCall := FunctionCall{
		FunctionName: function.FullName(),
		TaintSource:  fmt.Sprint(callSiteTaintedParamIndexSet),
	}
	if knownFunctionResult, ok := KnownInterfaceFunction[functionCall]; ok {
		log.Printf("%s is a known interface function\n", function.FullName())
		return &knownFunctionResult
	} else {
		log.Printf("%s is not a known interface function\n", function.FullName())
		log.Println(functionCall)
	}
	return nil
}

func GetKnownStaticFunction(function *ssa.Function, callSiteTaintedParamIndexSet []int) *FunctionTaintResult {
	if knownFunctionResult, ok := KnownStaticFunctionWithoutParam[function.String()]; ok {
		return &knownFunctionResult
	}

	functionCall := FunctionCall{
		FunctionName: function.String(),
		TaintSource:  fmt.Sprint(callSiteTaintedParamIndexSet),
	}
	if knownFunctionResult, ok := KnownStaticFunction[functionCall]; ok {
		log.Printf("%s is a known static function\n", function.String())
		return &knownFunctionResult
	}

	return nil
}

var (
	PackageSinks = map[string]bool{
		"log": true,
	}

	InterfaceFunctionSinks = map[string]bool{
		"(k8s.io/client-go/kubernetes/typed/apps/v1.StatefulSetsGetter).StatefulSets": true,
		"(github.com/go-logr/logr.Logger).Error":                                      true,
		"(github.com/go-logr/logr.Logger).Info":                                       true,
		"(k8s.io/client-go/tools/record.EventRecorder).Event":                         true, // this gets into events
	}

	StaticFunctionSinks = map[string]bool{
		"fmt.Errorf": true,
		"fmt.Printf": true,
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.SetControllerReference": true,
		"(*sigs.k8s.io/controller-runtime/pkg/builder.Builder).For":                           true,
		"k8s.io/apimachinery/pkg/api/errors.NewBadRequest":                                    true,
	}

	KnownStaticFunction = map[FunctionCall]FunctionTaintResult{
		{
			FunctionName: "sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.AddFinalizer",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:           false,
			TaintedParams: []int{0},
			TaintedRets:   []int{},
		},
		{
			FunctionName: "sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.AddFinalizer",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.File).Append",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:           false,
			TaintedParams: []int{0},
			TaintedRets:   []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.File).Append",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.Section).NewKey",
			TaintSource:  fmt.Sprint([]int{2}),
		}: {
			End:           false,
			TaintedParams: []int{0},
			TaintedRets:   []int{0},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.Section).NewKey",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:           false,
			TaintedParams: []int{0},
			TaintedRets:   []int{0},
		},
	}

	KnownStaticFunctionWithoutParam = map[string]FunctionTaintResult{
		"fmt.Sprintf": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"fmt.Sprint": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"net/url.escape": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"encoding/json.Marshal": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"encoding/json.Unmarshal": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"k8s.io/apimachinery/pkg/api/meta.Accessor": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).SetAnnotations": {
			End:           false,
			TaintedParams: []int{0},
			TaintedRets:   []int{},
		},
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.ContainsFinalizer": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).GetUID": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"k8s.io/utils/pointer.Int32Deref": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"k8s.io/apimachinery/pkg/labels.Parse": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).GetName": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/apimachinery/pkg/api/resource.Quantity).Cmp": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(k8s.io/apimachinery/pkg/api/resource.Quantity).Equal": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/api/core/v1.ResourceList).Memory": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/apimachinery/pkg/api/resource.Quantity).Value": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/apimachinery/pkg/api/resource.Quantity).IsZero": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"k8s.io/apimachinery/pkg/util/strategicpatch.StrategicMergePatch": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"reflect.DeepEqual": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
	}

	KnownInterfaceFunction = map[FunctionCall]FunctionTaintResult{
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.Reader).List",
			TaintSource:  fmt.Sprint([]int{2}),
		}: {
			End:           false,
			TaintedParams: []int{1},
			TaintedRets:   []int{},
		},
	}

	KnownInterfaceFunctionWithoutParam = map[string]FunctionTaintResult{
		"(sigs.k8s.io/controller-runtime/pkg/client.Reader).Get": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).GetName": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(error).Error": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).GetAnnotations": {
			End:           false,
			TaintedParams: []int{},
			TaintedRets:   []int{0},
		},
	}

	K8sInterfaceFunctions = map[string]bool{
		"(sigs.k8s.io/controller-runtime/pkg/client.Writer).Delete":    true,
		"(sigs.k8s.io/controller-runtime/pkg/client.Writer).Update":    true,
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).SetAnnotations": true,
	}

	K8sStaticFunctions = map[string]bool{
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.RemoveFinalizer": true,
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.CreateOrUpdate":  true,
	}
)

var BUILTIN_PROPOGATE = map[string]bool{
	"append":  true,
	"cap":     true,
	"complex": true,
	"copy":    true,
	"imag":    true,
	"len":     true,
	"make":    true,
	"new":     true,
	"real":    true,
}
