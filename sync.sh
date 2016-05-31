# A utility script to sync the smallgroup data to GitHub

cd ~/.smallgroup
git pull
git add .
git commit -m "sync"
git push --force