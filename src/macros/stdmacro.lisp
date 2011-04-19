; Standard macros for SoLISP
(def macro_dollar
     # [_ . items] => (+ '(@ _) items))

(def macro_match
     # [_ value . proc] => `('= proc value))

(= MACROS {
   "$" 		macro_dollar
   "match"	macro_match })
