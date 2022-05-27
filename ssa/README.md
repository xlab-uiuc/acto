## Value to CR fields mapping

### seed introduction
All values of type `seedType`

### Propogation rule

For instruction types:

    - Call: propogate to the specific parameter of the callee
    - TypeCast: simply propogate
        - ChangeInterface
        - ChangeType
        - Convert
    - Access children (root.spec, root.spec[0]): propogate with additional field name
        - Field: propogate with field name
        - FieldAddr: propogate with field name
        - Index: propogate with index
        - IndexAddr: propogate with index
        - LookUp: TODO if used as X, propogate
    - Phi: propogate with merged paths
    - UnOp: propogate if dereference
    - Store: TODO propogate backward
    - Return + Extract: TODO propogate to function callsites

### Sink:
    - Stop at all other instruction types
    - Stop propogation when calling library functions

---
## Data flow analysis
Find which CR fields do not end up in k8s client library functions

### Introduction
The results of the first pass

### Propogation rule

    - Instructions excluding the instructions used in the first pass

#### Challenges
- Interprocedural analysis  
    Call: propagate through interface calls  
    - We don't know the exact callee because interface methods may have multiple implementations. Propogate to all implementations
    Return + Extract: propogate to all the callsites
    - We don't know the exact callsite. Propogate to all possible callsites
    - If only one return value is tainted, need to make sure that Extract is handled
- Store
    propogate backwards
    - may need to propogate through parameters

### Taint checking:
- k8s client library function call  
    mark all the dependencies as true