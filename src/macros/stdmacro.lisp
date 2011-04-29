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

(def (macro_proc src) (+ '(=>) (src -> (: 1 None))))

(def (macro_assign_multi src)
     (+ '(begin)
	(tuple (for [left right] <- (src -> (: 1 None))
	            `('= left right)))))

(= MACROS {
   "$" 		macro_dollar
   "match"	macro_match
   "->"		macro_call_chain
   "@"          macro_proc
   "=*"		macro_assign_multi})
