name: Alarm Inspection Report
about: An analysis report for the alarms produced by Acto
labels: ''
body:
  - type: textarea
    id: problem
    attributes:
      label: What happened?
      description: |
        Why did Acto raise this alarm? What happened in the state transition? Why Acto’s oracles raised an alarm?
    validations:
      required: true

  - type: textarea
    id: root-cause
    attributes:
      label: What did you expect to happen?
    description: |
      Why did the operator behave in this way? Please find the exact block in the operator source code resulting in the behavior.
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Root Cause
    description: |
      If it is a true alarm, how to fix it in the operator code? If it is a false alarm, how to fix it in Acto code?
    validations:
      required: true
