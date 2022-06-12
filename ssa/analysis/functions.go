package analysis

import (
	"fmt"
	"go/types"
	"log"
	"os"

	"golang.org/x/tools/go/ssa"
)

func IsStaticFunctionSink(function *ssa.Function) bool {
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
	if function.Pkg() != nil && PackageSinks[function.Pkg().Name()] {
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

func GetKnownInterfaceFunction(functionCall FunctionCall) *FunctionTaintResult {
	if knownFunctionResult, ok := KnownInterfaceFunctionWithoutParam[functionCall.FunctionName]; ok {
		log.Printf("[%s] is a known interface function\n", functionCall.FunctionName)
		return &knownFunctionResult
	}

	if knownFunctionResult, ok := KnownInterfaceFunction[functionCall]; ok {
		log.Printf("%s is a known interface function\n", functionCall.FunctionName)
		return &knownFunctionResult
	} else {
		log.Printf("%s is not a known interface function\n", functionCall.FunctionName)
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
		log.Printf("%s is a known static function, it taints %s\n", function.String(), knownFunctionResult)
		return &knownFunctionResult
	}

	if function.Name() == "DeepCopy" {
		return &FunctionTaintResult{
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		}
	}

	if function.Name() == "DeepCopyInto" {
		return &FunctionTaintResult{
			End:         false,
			TaintedArgs: []int{1},
			TaintedRets: []int{},
		}
	}

	return nil
}

var (
	PackageSinks = map[string]bool{
		"log":     true,
		"reflect": true,
		"errors":  true,
	}

	InterfaceFunctionSinks = map[string]bool{
		"(k8s.io/client-go/kubernetes/typed/apps/v1.StatefulSetsGetter).StatefulSets":                     true,
		"(k8s.io/client-go/kubernetes/typed/apps/v1.StatefulSetInterface).Get":                            true,
		"(k8s.io/client-go/kubernetes/typed/core/v1.PersistentVolumeClaimInterface).Get":                  true,
		"(k8s.io/client-go/kubernetes/typed/core/v1.PersistentVolumeClaimsGetter).PersistentVolumeClaims": true,
		"(github.com/go-logr/logr.Logger).Error":                                                          true,
		"(github.com/go-logr/logr.Logger).Info":                                                           true,
		"(k8s.io/client-go/tools/record.EventRecorder).Event":                                             true, // this gets into events
	}

	StaticFunctionSinks = map[string]bool{
		"fmt.Errorf": true,
		"fmt.Printf": true,
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.SetControllerReference": true,
		"(*sigs.k8s.io/controller-runtime/pkg/builder.Builder).For":                           true,
		"k8s.io/apimachinery/pkg/api/errors.NewBadRequest":                                    true,
		"(*sigs.k8s.io/controller-runtime/pkg/scheme.Builder).Register":                       true,
	}

	KnownStaticFunction = map[FunctionCall]FunctionTaintResult{
		{
			FunctionName: "sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.AddFinalizer",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{0},
			TaintedRets: []int{},
		},
		{
			FunctionName: "sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.AddFinalizer",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.File).Append",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{0},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.File).Append",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.Section).NewKey",
			TaintSource:  fmt.Sprint([]int{2}),
		}: {
			End:         false,
			TaintedArgs: []int{0},
			TaintedRets: []int{0},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.Section).NewKey",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{0},
			TaintedRets: []int{0},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.Section).NewKey",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.File).WriteTo",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{1},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*gopkg.in/ini.v1.File).WriteTo",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
	}

	KnownStaticFunctionWithoutParam = map[string]FunctionTaintResult{
		"fmt.Sprintf": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"fmt.Sprint": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strings.Join": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strings.TrimSuffix": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strings.HasPrefix": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strings.TrimPrefix": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"net/url.escape": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"encoding/json.Marshal": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"encoding/json.Unmarshal": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"errors.Is": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/apimachinery/pkg/api/meta.Accessor": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).SetAnnotations": {
			End:         false,
			TaintedArgs: []int{0},
			TaintedRets: []int{},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).GetAnnotations": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.ContainsFinalizer": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).GetUID": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.Time).IsZero": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/apimachinery/pkg/api/errors.IsNotFound": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/utils/pointer.Int32Deref": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/apimachinery/pkg/labels.Parse": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).GetName": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/api/resource.Quantity).Cmp": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(k8s.io/apimachinery/pkg/api/resource.Quantity).Equal": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/api/core/v1.ResourceList).Memory": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/api/resource.Quantity).Value": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/api/resource.Quantity).IsZero": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/apimachinery/pkg/util/strategicpatch.StrategicMergePatch": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/client-go/rest.Request).VersionedParams": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"reflect.DeepEqual": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/client-go/rest.Request).URL": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*gopkg.in/ini.v1.File).Section": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
	}

	KnownInterfaceFunction = map[FunctionCall]FunctionTaintResult{
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.Reader).List",
			TaintSource:  fmt.Sprint([]int{2}),
		}: {
			End:         false,
			TaintedArgs: []int{1},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.Reader).List",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
	}

	KnownInterfaceFunctionWithoutParam = map[string]FunctionTaintResult{
		"(sigs.k8s.io/controller-runtime/pkg/client.Reader).Get": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*k8s.io/apimachinery/pkg/apis/meta/v1.ObjectMeta).GetName": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(error).Error": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).GetAnnotations": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
	}

	K8sInterfaceFunctions = map[string]bool{
		"(sigs.k8s.io/controller-runtime/pkg/client.Writer).Delete":       true,
		"(sigs.k8s.io/controller-runtime/pkg/client.Writer).Update":       true,
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).SetAnnotations":    true,
		"(sigs.k8s.io/controller-runtime/pkg/client.StatusWriter).Update": true,
	}

	K8sStaticFunctions = map[string]bool{
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.RemoveFinalizer": true,
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.CreateOrUpdate":  true,
		"k8s.io/client-go/tools/remotecommand.NewSPDYExecutor":                         true,
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

func DumpKnownFunctions() {
	outFile, err := os.Create("knownFunctions.txt")
	if err != nil {
		log.Fatalf("Failed to create file %s\n", err)
	}

	for f, tainted := range KnownStaticFunction {
		outFile.WriteString(fmt.Sprintf("Function %s has taints\n", f))
		outFile.WriteString(fmt.Sprintf("\t%s\n", &tainted))
	}

	for f, tainted := range KnownInterfaceFunction {
		outFile.WriteString(fmt.Sprintf("Function %s has taints\n", f))
		outFile.WriteString(fmt.Sprintf("\t%s\n", &tainted))
	}
}
