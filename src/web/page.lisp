(import web.dom)
(= ht web.dom.dom)

(widget (page content :title "United")
 (ht.html
   (ht.head (ht.title title))
   (ht.body content)))

(widget (ul_list content)
 (ht.ul
   (for item <- content (ht.li item))))

(widget (section content :title "No Title")
	[ (ht.h1 title) content])


(= TEST_PAGE
   (page :title "Test My page"
    (section
     (ht.p "Blahl blhal blhal")
     (ul_list
      "First One"
      (ht.span "Second One" (ht.a :href "http://www.google.com" "LOL"))
      "Last One"))))

