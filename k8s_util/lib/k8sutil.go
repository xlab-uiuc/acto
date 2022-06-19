package main

import "C"
import (
	"fmt"

	"k8s.io/apimachinery/pkg/api/resource"
)

// type Scale int32
// type infDecAmount struct {
// 	*inf.Dec
// }

// const (
// 	Nano Scale = -9
// )

// func (s Scale) infScale() inf.Scale {
// 	return inf.Scale(-s) // inf.Scale is upside-down
// }

//export parse
func parse(valuePtr *C.char) *C.char {
	value := C.GoString(valuePtr)
	q, err := resource.ParseQuantity(value)
	if err != nil {
		return C.CString(value)
	}
	// return C.CString(strconv.FormatInt(q.Value(), 10))
	return C.CString(q.AsDec().String())
}

// func parseQuantityString(str string) (positive bool, value, num, denom, suffix string, err error) {
// 	positive = true
// 	pos := 0
// 	end := len(str)

// 	// handle leading sign
// 	if pos < end {
// 		switch str[0] {
// 		case '-':
// 			positive = false
// 			pos++
// 		case '+':
// 			pos++
// 		}
// 	}

// 	// strip leading zeros
// Zeroes:
// 	for i := pos; ; i++ {
// 		if i >= end {
// 			num = "0"
// 			value = num
// 			return
// 		}
// 		switch str[i] {
// 		case '0':
// 			pos++
// 		default:
// 			break Zeroes
// 		}
// 	}

// 	// extract the numerator
// Num:
// 	for i := pos; ; i++ {
// 		if i >= end {
// 			num = str[pos:end]
// 			value = str[0:end]
// 			return
// 		}
// 		switch str[i] {
// 		case '0', '1', '2', '3', '4', '5', '6', '7', '8', '9':
// 		default:
// 			num = str[pos:i]
// 			pos = i
// 			break Num
// 		}
// 	}

// 	// if we stripped all numerator positions, always return 0
// 	if len(num) == 0 {
// 		num = "0"
// 	}

// 	// handle a denominator
// 	if pos < end && str[pos] == '.' {
// 		pos++
// 	Denom:
// 		for i := pos; ; i++ {
// 			if i >= end {
// 				denom = str[pos:end]
// 				value = str[0:end]
// 				return
// 			}
// 			switch str[i] {
// 			case '0', '1', '2', '3', '4', '5', '6', '7', '8', '9':
// 			default:
// 				denom = str[pos:i]
// 				pos = i
// 				break Denom
// 			}
// 		}
// 		// TODO: we currently allow 1.G, but we may not want to in the future.
// 		// if len(denom) == 0 {
// 		// 	err = ErrFormatWrong
// 		// 	return
// 		// }
// 	}
// 	value = str[0:pos]

// 	// grab the elements of the suffix
// 	suffixStart := pos
// 	for i := pos; ; i++ {
// 		if i >= end {
// 			suffix = str[suffixStart:end]
// 			return
// 		}
// 		if !strings.ContainsAny(str[i:i+1], "eEinumkKMGTP") {
// 			pos = i
// 			break
// 		}
// 	}
// 	if pos < end {
// 		switch str[pos] {
// 		case '-', '+':
// 			pos++
// 		}
// 	}
// Suffix:
// 	for i := pos; ; i++ {
// 		if i >= end {
// 			suffix = str[suffixStart:end]
// 			return
// 		}
// 		switch str[i] {
// 		case '0', '1', '2', '3', '4', '5', '6', '7', '8', '9':
// 		default:
// 			break Suffix
// 		}
// 	}
// 	// we encountered a non decimal in the Suffix loop, but the last character
// 	// was not a valid exponent
// 	// err = ErrFormatWrong
// 	return
// }

func main() {
	// fmt.Println("Hello, world.")
	test := "-.1Ki"
	ans, err := resource.ParseQuantity(test)
	if err == nil {
		fmt.Println(ans.Value())
		// 	fmt.Println(ans.ScaledValue(0))
		// 	fmt.Println("parsed value:", ans.Value())
		// 	fmt.Println("parsed format:", ans.Format)
	}
	// positive, value, num, denom, suffix, err := parseQuantityString(test)
	// if err != nil {
	// 	fmt.Println("error")
	// }
	// fmt.Println("positive:", positive)
	// fmt.Println("value:", value)
	// fmt.Println("num:", num)
	// fmt.Println("denom:", denom)
	// fmt.Println("suffix:", suffix)
	// mantissa := int64(int64(1) << uint64(10))
	// fmt.Println("mantissa:", mantissa)
	// amount := new(inf.Dec)
	// if _, ok := amount.SetString(value); !ok {
	// 	fmt.Println("error")
	// }
	// // amount == -0.01
	// numericSuffix := big.NewInt(1).Lsh(big.NewInt(1), uint(10))
	// ub := amount.UnscaledBig()
	// // amount == -0.01
	// amount.SetUnscaledBig(ub.Mul(ub, numericSuffix))
	// // amount == -10.24

	// sign := amount.Sign()
	// if sign == -1 {
	// 	amount.Neg(amount)
	// }
	// // 10.24
	// if v, ok := amount.Unscaled(); v != int64(0) || !ok {
	// 	amount.Round(amount, Nano.infScale(), inf.RoundUp)
	// } // 10.240000000

	// maxAllowed := infDecAmount{inf.NewDec((1<<63)-1, 0)}
	// if amount.Cmp(maxAllowed.Dec) > 0 {
	// 	amount.Set(maxAllowed.Dec)
	// }
	// decZero := inf.NewDec(0, 0)
	// decOne := inf.NewDec(1, 0)
	// if amount.Cmp(decOne) < 0 && amount.Cmp(decZero) > 0 {
	// 	// This avoids rounding and hopefully confusion, too.
	// 	fmt.Println("decimal")
	// }
	// if sign == -1 {
	// 	amount.Neg(amount)
	// }

	// fmt.Println(infDecAmount{amount})
}
