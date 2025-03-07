# small-group
A small local web app I built to store information about our Bible study small group and use it to divide us into smaller groups for Bible study.

# how to install
Make sure you have the dependencies:

- Python 3
- `tinydb`
- `flask`

Make sure you have a **private** GitHub repository specially designated for synchronizing your data. (Emphasis on **private**: Neither myself nor the app are responsible if your data becomes publicly available.) Follow the instructions below.

    $ mkdir ~/.smallgroup
    $ cd ~/.smallgroup
    $ git remote add origin <your private github repository URL>
    $ git push --set-upstream origin master

Once this is done, synchronization is done automatically each time you run the app (instructions below). There is a script called [`sync.sh`](./sync.sh) that handles this.

Clone the repository and run the Flask app locally:

    $ cd /path/to/your/favorite/dir
    $ git clone https://github.com/ericmjl/small-group.git
    $ cd small-group
    $ python app.py

You can open the app in your browser at the URL: `http://localhost:5000/`

To close the app, close the terminal window in which you ran the app.

# contributing & feature requests
Software is provided as-is. I add features only if I find them useful for my own small group. If you have suggestions, put in an issue, and I'll make a final call on whether I will implement it. If I don't, it's nothing personal, I just don't have the bandwidth (having a full-time job as a science researcher).

On the other hand, pull requests with new or original code contributions are always welcome.

# faq
**Q: Where are my small group member data stored?**

A: They are stored in your home directory. The exact path is: `~/.smallgroup/members.json`.

**Q: What is the algorithm for dividing group members?**

A: The algorithm maximizes the summed Shannon diversity across the "Faith Status", "Role" and "Gender" columns. You can find it in the [`smallgroup.py`](./smallgroup.py) file.
