module grad-checker/tests

go 1.22

require (
	grad-checker/api v0.0.0
	grad-checker/subjects v0.0.0
)

replace grad-checker/api => ../api

replace grad-checker/subjects => ../modules/subjects
