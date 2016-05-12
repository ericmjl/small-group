# small-group
A local web app I built to store information about our Bible Study small group and use it to divide us into smaller groups.

# how to install

Make sure you have the dependencies:

- Python 3
- `tinydb`
- `flask`

Clone the repository and run the Flask app locally:

    $ cd /path/to/your/favorite/dir
    $ git clone https://github.com/ericmjl/small-group.git
    $ cd small-group
    $ python app.py

Make sure you have a private GitHub repository for synchronizing your data. 

# contributing & feature requests
Software is provided as-is. I add features only if I find them useful for my own small group. If you have suggestions, put in an issue, and I'll make a final call on whether I will implement it.

Pull requests are always welcome.

# faq

**Q: Where are my small group member data stored?**
A: They are stored in your home directory. The exact path is: `~/.smallgroup/members.json`.