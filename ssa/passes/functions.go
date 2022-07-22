package analysis

import (
	"fmt"
	"go/types"
	"log"
	"os"

	"golang.org/x/tools/go/ssa"
)

func IsStaticFunctionSink(function *ssa.Function) bool {
	if function.Pkg != nil && PackageSinks[function.Pkg.Pkg.Path()] {
		return true
	}

	if StaticFunctionSinks[function.String()] {
		log.Printf("static function %s is sink\n", function.String())
		return true
	}
	return false
}

func IsInterfaceFunctionSink(function *types.Func) bool {
	if function.Pkg() != nil && PackageSinks[function.Pkg().Path()] {
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

	if knownFunctionResult, ok := KnownFunctionWithoutReceiver[function.Name()]; ok {
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
		"log":                           true,
		"reflect":                       true,
		"github.com/pkg/errors":         true,
		"github.com/go-logr/logr":       true,
		"github.com/go-openapi/runtime": true,
		"k8s.io/klog/v2":                true,
		"github.com/Azure/azure-storage-blob-go/azblob": true,
		"github.com/hashicorp/go-version":               true,
		"database/sql":                                  true,
	}

	StructSinks = map[string]bool{
		"(*k8s.io/apimachinery/pkg/apis/meta/v1/unstructured.Unstructured)": true,
	}

	InterfaceFunctionSinks = map[string]bool{
		"(k8s.io/client-go/kubernetes/typed/apps/v1.StatefulSetsGetter).StatefulSets":                     true,
		"(k8s.io/client-go/kubernetes/typed/apps/v1.StatefulSetInterface).Get":                            true,
		"(k8s.io/client-go/kubernetes/typed/core/v1.PersistentVolumeClaimInterface).Get":                  true,
		"(k8s.io/client-go/kubernetes/typed/core/v1.PersistentVolumeClaimsGetter).PersistentVolumeClaims": true,
		"(github.com/go-logr/logr.Logger).Error":                                                          true,
		"(github.com/go-logr/logr.Logger).Info":                                                           true,
		"(k8s.io/client-go/tools/record.EventRecorder).Event":                                             true, // this gets into events
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).GetLabels":                                         true,
		"(k8s.io/client-go/tools/record.EventRecorder).Eventf":                                            true,
		"(sigs.k8s.io/controller-runtime/pkg/client.Reader).List":                                         true,
		"(sigs.k8s.io/controller-runtime/pkg/client.StatusClient).Status":                                 true,
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).SetOwnerReferences":                                true,
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).GetOwnerReferences":                                true,
		"k8s.io/apimachinery/pkg/apis/meta/v1.IsControlledBy":                                             true,
		"(sigs.k8s.io/controller-runtime/pkg/controller.Controller).Watch":                                true,
	}

	StaticFunctionSinks = map[string]bool{
		"context.WithTimeout":                    true,
		"fmt.Errorf":                             true,
		"fmt.Printf":                             true,
		"strings.Contains":                       true,
		"strings.Index":                          true,
		"(*k8s.io/client-go/rest.Request).Watch": true,
		"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil.SetControllerReference": true,
		"(*sigs.k8s.io/controller-runtime/pkg/builder.WebhookBuilder).For":                    true,
		"(*sigs.k8s.io/controller-runtime/pkg/builder.WebhookBuilder).registerWebhooks":       true,
		"(*sigs.k8s.io/controller-runtime/pkg/builder.Builder).For":                           true,
		"k8s.io/apimachinery/pkg/api/errors.NewBadRequest":                                    true,
		"(*sigs.k8s.io/controller-runtime/pkg/scheme.Builder).Register":                       true,
		"sigs.k8s.io/controller-runtime/pkg/client/fake.NewFakeClient":                        true,
		"sigs.k8s.io/controller-runtime/pkg/client/apiutil.GVKForObject":                      true,
		"(*k8s.io/apimachinery/pkg/runtime.Scheme).AddKnownTypes":                             true,
		"k8s.io/kubernetes/pkg/util/hash.DeepHashObject":                                      true,
		"unicode/utf8.Valid":    true,
		"net.LookupIP":          true,
		"(*net/http.Client).do": true,
		"sigs.k8s.io/controller-runtime/pkg/client.IgnoreNotFound":                       true,
		"(*github.com/hashicorp/go-version.Version).Compare":                             true,
		"(*k8s.io/client-go/rest.Request).Do":                                            true,
		"k8s.io/client-go/transport/spdy.RoundTripperFor":                                true,
		"k8s.io/client-go/kubernetes.NewForConfigOrDie":                                  true,
		"(*database/sql.DB).Exec":                                                        true,
		"(*k8s.io/apimachinery/pkg/apis/meta/v1/unstructured.Unstructured).SetName":      true,
		"(*k8s.io/apimachinery/pkg/apis/meta/v1/unstructured.Unstructured).SetNamespace": true,
	}

	KnownFunctionWithoutReceiver = map[string]FunctionTaintResult{
		"DeepCopy": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"DeepCopyInto": {
			End:         false,
			TaintedArgs: []int{1},
			TaintedRets: []int{},
		},
	}

	KnownStaticFunction = map[FunctionCall]FunctionTaintResult{
		{
			FunctionName: "(*sync.Map).LoadOrStore",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{0},
			TaintedRets: []int{},
		},
		{
			FunctionName: "strconv.ParseInt",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		{
			FunctionName: "strings.Replace",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		{
			FunctionName: "strings.ReplaceAll",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		{
			FunctionName: "(k8s.io/client-go/rest.Result).Into",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*k8s.io/client-go/rest.Request).Body",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*k8s.io/client-go/rest.Request).Body",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         true,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
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
		{
			FunctionName: "gopkg.in/yaml.v2.Unmarshal",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		{
			FunctionName: "(*text/template.Template).Execute",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{1},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*text/template.Template).Execute",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(*text/template.Template).Execute",
			TaintSource:  fmt.Sprint([]int{2}),
		}: {
			End:         false,
			TaintedArgs: []int{1},
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
		"fmt.Fprintf": {
			End:         false,
			TaintedArgs: []int{0},
			TaintedRets: []int{},
		},
		"strings.Split": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strings.EqualFold": {
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
		"strings.ToLower": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strconv.Itoa": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strconv.FormatBool": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"strconv.ParseFloat": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"sort.Strings": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"net/url.escape": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"net/url.Parse": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"net.ParseIP": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"net/http.NewRequest": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(net/url.Values).Encode": {
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
		"encoding/pem.Decode": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0, 1},
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
		"k8s.io/apimachinery/pkg/labels.SelectorFromSet": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/apimachinery/pkg/util/intstr.FromInt": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/kubernetes/pkg/util/slice.ContainsString": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"k8s.io/apimachinery/pkg/util/validation.IsDNS1035Label": {
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
		"sigs.k8s.io/controller-runtime/pkg/client.MergeFrom": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
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
		"(k8s.io/apimachinery/pkg/types.NamespacedName).String": {
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
		"(*regexp.Regexp).MatchString": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"(*regexp.Regexp).FindAllString": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"regexp.Compile": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"github.com/hashicorp/go-version.NewVersion": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
		"github.com/hashicorp/go-version.Must": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
	}

	KnownInterfaceFunction = map[FunctionCall]FunctionTaintResult{
		{
			FunctionName: "(k8s.io/client-go/kubernetes/typed/core/v1.PersistentVolumeClaimInterface).Patch",
			TaintSource:  fmt.Sprint([]int{3}),
		}: {
			End:         true,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(k8s.io/client-go/kubernetes/typed/batch/v1.JobInterface).Create",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         true,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(k8s.io/apimachinery/pkg/apis/meta/v1.Object).SetLabels",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{-1},
			TaintedRets: []int{},
		},
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
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.StatusWriter).Patch",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.StatusWriter).Patch",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         true,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.Writer).Patch",
			TaintSource:  fmt.Sprint([]int{-1}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.Writer).Patch",
			TaintSource:  fmt.Sprint([]int{0}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.Writer).Patch",
			TaintSource:  fmt.Sprint([]int{1}),
		}: {
			End:         true,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(sigs.k8s.io/controller-runtime/pkg/client.Writer).Patch",
			TaintSource:  fmt.Sprint([]int{2}),
		}: {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{},
		},
		{
			FunctionName: "(github.com/go-openapi/runtime.ClientTransport).Submith",
			TaintSource:  fmt.Sprint([]int{-1}),
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
			TaintedRets: []int{},
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
		"(k8s.io/apimachinery/pkg/labels.Selector).Add": {
			End:         false,
			TaintedArgs: []int{},
			TaintedRets: []int{0},
		},
	}

	K8sInterfaceFunctions = map[string]bool{
		"(sigs.k8s.io/controller-runtime/pkg/client.Writer).Create":                         true,
		"(sigs.k8s.io/controller-runtime/pkg/client.Writer).Delete":                         true,
		"(sigs.k8s.io/controller-runtime/pkg/client.Writer).Update":                         true,
		"(k8s.io/apimachinery/pkg/apis/meta/v1.Object).SetAnnotations":                      true,
		"(sigs.k8s.io/controller-runtime/pkg/client.StatusWriter).Update":                   true,
		"(k8s.io/client-go/kubernetes/typed/core/v1.ConfigMapInterface).Create":             true,
		"(k8s.io/client-go/kubernetes/typed/apps/v1.StatefulSetInterface).Create":           true,
		"(k8s.io/client-go/kubernetes/typed/apps/v1.StatefulSetInterface).UpdateScale":      true,
		"(k8s.io/client-go/kubernetes/typed/core/v1.ServiceInterface).Create":               true,
		"(k8s.io/client-go/kubernetes/typed/apps/v1.DeploymentInterface).Create":            true,
		"(k8s.io/client-go/kubernetes/typed/core/v1.PersistentVolumeClaimInterface).Update": true,
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
