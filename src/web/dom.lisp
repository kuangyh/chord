;; Page creation in LISP
(import cgi)
(import cStringIO)

(= flatten_list
   (# ls :list =>
      (for x <- ls (emit* (flatten_list x)) (cont))
    # => [_]))

(class FormattedString :str)

(class Element
   (def (__init__ self tag attrs content)
	(= self.tag tag)
	(= self.attrs attrs)
	(= self.content content)
	None)

   (def (dump self fp)
	(fp.write
	  (+ "<" self.tag " "
	     ((@ " " join) (for [k v] <- (self.attrs.iteritems)
				(+ k "=\"" (cgi.escape (str v)) "\"")))
	     ">"))
	(for x <- self.content
	     (match x
	      # :Element => (x.dump fp)
	      # :FormattedString => (fp.write x)
	      # => (fp.write (cgi.escape (str x)))))
	(fp.write (% "</%s>" self.tag))
	None)

   (def (dumps self)
	(= io (cStringIO.StringIO))
	(self.dump io)
	(FormattedString (io.getvalue))))

(class Helper
   (def (element self tag . content .. attrs)
	(Element tag attrs (flatten_list (list content))))
   (= __call__ element)

   (def (__getattr__ self tag)
	(fn ( . content .. attrs) (self.element tag . content .. attrs))))

(= dom (Helper))

