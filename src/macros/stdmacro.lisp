; Standard macros for SoLISP
(def macro_dollar
     # [_ . items] => (+ '(_ ->) items))

(def macro_match
     # [_ value . proc] => `('= proc value))

(def macro_call_chain
     # [_ head . chain] =>
       (loop [curr [chain_head . chain_remain]] <- [head chain]
  	     (cont [`(chain_head curr) chain_remain]))
       curr)

(= MACROS {
   "$" 		macro_dollar
   "match"	macro_match
   "!"		macro_call_chain })
