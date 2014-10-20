#!/bin/sh  
 
# usage:
# script-name -> list all branches and their author / last commit author
# script-name 'author name' -> lists only branches by given author
 
git branch -r | while read branch
do
  name=`git log --pretty=tformat:%an -1 $branch`
  if [ $# -gt 0 ] && [ "$name" == "$1" ]   
  then    
    echo $branch : $name
  fi      
 
  if [ $# -eq 0 ]
  then
    echo $branch : $name  
  fi
done
