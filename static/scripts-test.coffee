window.search = () ->
    input = document.getElementById('searchNames')
    filter = input.value.toUpperCase()

    # Select the active members' table rows.
    tableActive = document.getElementById("table-active")
    trActive = tableActive.getElementsByTagName("tr")

    # Select the inactive members' table rows.
    tableInactive = document.getElementById("table-inactive")
    trInactive = tableInactive.getElementsByTagName("tr")

    find = (trs) ->
        for tr, i in trs
            for td in tr.getElementsByTagName("td")
                if td.innerHTML.toUpperCase().indexOf(filter) > -1
                    trs[i].style.display = ""
                else
                    trs[i].style.display = "none"
    find(trActive)
    find(trInactive)
