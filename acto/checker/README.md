## Custom Checkers Implementation Guide

The provided code includes a framework for implementing custom checkers in Acto.
Checkers are used to verify the correctness of system behavior snapshots.
This guide will walk you through the steps to implement custom checkers for your specific use cases.

## Overview

The Acto library defines a base `Checker` class and two subclasses, `UnaryChecker` and `BinaryChecker`,
which you can use as a starting point for your custom checkers.

Checkers are responsible for analyzing system behavior snapshots and producing `OracleResult` objects,
indicating whether the snapshot passes the checker's criteria or not,
and deciding what `system input` will be in the next step of the trial.

## Implementing a Custom Checker

To create a custom checker, follow these steps:

### Step 1: Import Required Modules

Before implementing your custom checker, make sure to import the necessary modules from the Acto library:

```python
from acto.snapshot import Snapshot
from acto.checker.checker import Checker, UnaryChecker, BinaryChecker, OracleResult, OracleControlFlow
```

### Step 2: Define Your Checker Class

Define a new class that extends either the `UnaryChecker` or `BinaryChecker` class based on the type of snapshot comparison your checker requires.
If your checker involves three or more concussive snapshots, you can directly extend `Checker`, and `recovery.py` is an example for you.

For example, if your checker only needs to analyze a single snapshot, extend the `UnaryChecker` class:

```python
from acto.snapshot import Snapshot
from acto.checker.checker import UnaryChecker, OracleResult, OracleControlFlow
class MyUnaryChecker(UnaryChecker):
    name = "MyUnaryChecker"

    def __init__(self, **kwargs):
        # Your initialization logic here (if any)
        pass

    def _unary_check(self, snapshot: Snapshot) -> OracleResult:
        # Your custom checker logic here
        # ...
        # Return an OracleResult object with the appropriate message and control flow
        return OracleResult(message=OracleControlFlow.ok)
```

If your checker needs to compare two snapshots, extend the `BinaryChecker` class:

```python
from acto.snapshot import Snapshot
from acto.checker.checker import BinaryChecker, OracleResult, OracleControlFlow
class MyBinaryChecker(BinaryChecker):
    name = "MyBinaryChecker"

    def __init__(self, **kwargs):
        # Your initialization logic here (if any)
        pass

    def _binary_check(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        # Your custom checker logic here
        # ...
        # Return an OracleResult object with the appropriate message and control flow
        return OracleResult(message=OracleControlFlow.ok)
```

### Step 3: Implement Your Checker Logic

In the `_unary_check` (for `UnaryChecker`) or `_binary_check` (for `BinaryChecker`) method, write the custom logic to analyze the given snapshots.
The `snapshot` parameter represents the current snapshot, and `prev_snapshot` (only available for `BinaryChecker`) represents the previous snapshot in the system's behavior.

If your checker involves three or more concussive snapshots,
you can use `Snapshot.parent` to access the previous snapshot of the current snapshot.

Your custom logic can include various checks, comparisons, and evaluations based on the attributes and properties of the snapshots.
Depending on the result of the analysis, create an `OracleResult` object with an appropriate message and control flow.

### Step 4: Return an OracleResult

The final step in your checker's logic is to create an `OracleResult` object and return it.
The `OracleResult` object communicates the outcome of the checker's analysis.
The result's `means` method should be used to check the `OracleControlFlow` enum values (`ok`, `flush`, `revert`, `terminate`, or `redo`),
indicating the checker's decision based on the analysis.

For example, if the snapshot passes your custom checker's criteria, you can create an `OracleResult` object as follows:

```python
from dataclasses import dataclass

from acto.snapshot import Snapshot
from acto.checker.checker import UnaryChecker, OracleResult, OracleControlFlow, means_first

@dataclass
class CustomOracleResult(OracleResult):
    threshold: float = 10.0
    average: float = 10.0

    @means_first(lambda self: not self.means_terminate())
    def means_ok(self):
        return self.average < self.threshold
    
    @means_first(lambda self: not self.means_terminate())
    def means_revert(self):
        return self.average >= self.threshold

class MyCustomChecker(UnaryChecker):
    name = "MyCustomChecker"
    
    def __init__(self, threshold: float = 10.0, **kwargs):
        # Your initialization logic here (if any)
        super().__init__(**kwargs)
        self.threshold = threshold
    
    def _unary_check(self, snapshot: Snapshot) -> OracleResult:
        # Your custom checker logic here
        average_value = calculate_average(snapshot)  # Replace this with your logic
        return CustomOracleResult(threshold=self.threshold, average=average_value)
```

In this example, we assume that we have a function `calculate_average(snapshot)` that calculates the average value of a list of numbers in the snapshot.
You would replace this function with your custom logic to compute the average value based on your specific use case.

We then set a threshold value (`threshold = 10.0`), which represents the minimum average value required for the snapshot to be considered “ok.”

We return a `CustomOracleResult` object with the `means_ok` and `means_revert` method implemented to check whether the average value is greater than the threshold. This provides additional information about the average value in the `CustomOracleResult` object.

With this implementation, your custom checker can now provide specific information about the average value of the snapshot when it is considered “ok” based on your custom logic.

To check if a result represents a particular `OracleControlFlow`, use the `means` method. For example, to check if the result means `ok`, you can use:

```python
if result.means(OracleControlFlow.ok):
    # Handle the case when the result means "ok"
```

### Step 5: Enable/Disable the Checker (Optional)

If you want your checker to be enabled or disabled under certain conditions, you can override the `enabled` method in your custom checker class.

```python
def enabled(self, snapshot: Snapshot) -> bool:
    # Your logic to enable or disable the checker based on the snapshot
    # Return True to enable the checker, False to disable it
    return True
```

Certainly! Here's the revised Step 6, focusing on registering your custom checker `MyCustomChecker` with the `CheckerSet`:

### Step 6: Storing and Accessing State in the Snapshot (Optional)

In the updated `Snapshot` class, two new functions,
`get_context_value` and `set_context_value`,
have been introduced to provide a mechanism for storing and accessing state information within the snapshot.
These functions enable the storage of arbitrary key-value pairs,
allowing users to keep track of additional contextual information during the trial execution.

### Example Use Case

Let's consider a use case where you want to keep track of the number of retries for a specific test case within a trial.
You can use `set_context_value` and `get_context_value` to achieve this:

```python
# Assuming 'snapshot' is an instance of the Snapshot class

# Retrieving the number of retries (if it exists) or initializing it to 0
retries = snapshot.get_context_value("retries") or 0

# Incrementing the number of retries after each attempt
retries += 1

# Storing the updated number of retries back in the context
snapshot.set_context_value("retries", retries)

# Later in the trial, you can access the retries value again
new_retries = snapshot.get_context_value("retries")
```

By using the context storage,
you can maintain and update the state of different variables or values during the trial's execution,
making it easier to track and manage relevant information.

**Note**: Keep in mind that the context storage is specific to each snapshot and its descendants within a trial.
The information stored in one trial won't be accessible in another trial.

Feel free to utilize `get_context_value` and `set_context_value` in your custom checkers or any other parts of the trial logic to store and retrieve state information as needed during the trial's execution.

### Step 7: Register Your Custom Checker

Once you have implemented your custom checker, you can register it with the `CheckerSet` to make it available for use in your trials.
You can do this by adding `MyCustomChecker` to the list of `checker_generators` when creating the `CheckerSet` object.

```python
from acto.checker.checker_set import CheckerSet, default_checker_generators

# ... Your custom checker class MyCustomChecker ...

# Create a new instance of the CheckerSet and include MyCustomChecker in the list of checker_generators
checker_set = CheckerSet(context=your_context_dict, input_model=your_input_model, checker_generators=[MyCustomChecker] + default_checker_generators)
```

In this example, we added `MyCustomChecker` to the list of `checker_generators` by using the `+` operator. This ensures that your custom checker will be included alongside the default checkers (`default_checker_generators`) when creating the `CheckerSet`.

Now, your `MyCustomChecker` will be available in the `checker_set`, and it will be used in trials along with the other default checkers to evaluate snapshots and provide custom feedback based on your checker's specific criteria.

## Conclusion

Congratulations! You have now implemented a custom checker for Acto.
Your checker can now be used alongside other built-in checkers to analyze snapshots and verify the correctness of your system's behavior during trials.
Remember to register your custom checker with the `CheckerSet` before executing your trials to enable its functionality. Happy testing!
