; Standard macros for SoLISP
(def (macro_dollar src)
     ; Fetch properties of current context
     ; Very useful in pattern matching code
     (+ '(@ _) (@ src (: 1 None))))

(= macro_match (# ['match value . proc] => `('= proc value)))

(def (macro_exec src) `((@ src :1) '_))

(= MACROS {
   "$" 		macro_dollar
   "match"	macro_match
   "!"		macro_exec
   })
