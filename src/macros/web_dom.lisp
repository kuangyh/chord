;; Macros to make defining widget easier
(def (macro_widget src)
     (= [_ [name . proto] . body] src)
     `('begin
       '(import "web.dom")
       `('def `(name '. '_c '.. '_a)
	 `((+ `('fn (tuple proto)) (tuple body))
	   '(web.dom.flatten_list (list _c)) '.. '_a))))

(= MACROS
   { "widget" macro_widget })
