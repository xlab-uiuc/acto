Google Drive Directory
https://drive.google.com/drive/folders/12XY6WmReuhvX2Du6KqB4xiFC3YEzRqMM

Google Sheet for list of operators in the wild
https://docs.google.com/spreadsheets/d/1_3-SlBRJO0Gtj6gt2Go1cOi4iRHdeBquoV-04Yel74A/edit?usp=sharing

Operator Porting Tracker
https://docs.google.com/spreadsheets/d/1qeMk4m8D8fgJdI61QJ67mBHZ9m3gCD-axcJB567z5FM/edit#gid=0

## Measure code coverage for Acto
Golang does not have many tools for measuring code coverage except the native `go test` util.
However, `go test` does not support measuring code coverage for E2E tests, it only supports 
measuring code coverage on unit/integration level.

We use a series of hacks to measure the code coverage for Acto:
1. Create a new file called `main_test.go` under the same directory with the `main.go`, the `main_test.go` 
should contain one unittest which calls the `main` function. In this way, we created a virtual
unittest which just runs the `main` function, essentially an E2E test.
2. Next, we need to compile this unittest into a binary and build a docker image on it. Luckily, 
`go test` supports `-c` flag which compiles the unittest into a binary to be run later instead of 
running it immediately. We then modify the `Dockerfile` to change the build command from `go build ...`
to `go test -c ...` with approriate flags. Along with the build flags, we also pass in the test flags
such as `-coverpkg -cover`.
3. Having the test binary is not enough, we need to pass in a flag when running the binary to redirect 
the coverage information to a file. To do this, we need to create a shell script which exec the binary 
with the `-test.coverprofile=/tmp/profile/cass-operator-``date +%s%N``.out` flag and make this shell 
script the entrypoint of the docker image.