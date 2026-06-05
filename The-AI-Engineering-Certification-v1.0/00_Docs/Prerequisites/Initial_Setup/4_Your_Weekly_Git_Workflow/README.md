# 🧑‍💻 Your Version Control Workflow

We can break down your specific workflow into two distinct Gitflows for the course:

1. Initial Setup: Setting Up Your Local and Remote Git Repos
2. Weekly Workflow: Working on Assignments

In this walkthrough, we’ll cover the Weekly Workflow

## **Part II: Working on Assignments**

You might be wondering: "*How do I actually do my class assignments?* 

Short answer: **Like this!**

![image](https://i.imgur.com/7TA9TIu.png)

Let’s walk through the process that you’ll use to *work on assignments and submit them via your remote repository on GitHub.com*.

### 0️⃣ Pre-Requisites

First, make sure that you’ve followed `Part I: Setting Up Your Local and Remote Git Repos` 

Now, imagine you want to pull down week 2’s work *as the assignment is released as class begins*!

### 1️⃣ Pull New Course Materials

Run this command:

```markdown
git pull upstream main --allow-unrelated-histories
```

### 2️⃣ Do Assignment

Make changes, do the homework

`... do your work ...`

Run this command before to prepare your new (staged) content for a commit (to production, let’s say).

```markdown
git add .
```

🎉 Congrats! *You just moved changes from your working directly to the staging area (also called the index)!*

### 3️⃣ Your First [Commit](https://git-scm.com/docs/git-commit)

Create a new commit that includes a log message describing the changes you’ve made.

```markdown
git commit -m "Completed lesson 1 assignment"
```

*You just recorded the changes to your repo.*

### 4️⃣ Push to Your Remote

Now that we’re done with our assignment, we can overwrite the old unfinished assignment on our remote repository with our new finished code!

```markdown
git push origin main
```

🎉 Congrats! *You just pushed your changes to production (your live, remote, always-on repo)!*

### 5️⃣ Repeat Weekly!

Now imagine you’re about to start **week 3**’s work! Can you recall the steps you need to follow and why?

```markdown
git pull upstream main --allow-unrelated-histories # Get new lesson materials from AI Makerspace remote
#--do work--
git add . # Add changes to git history / move changes to staging 
git commit -m "Completed lesson X assignment" # Commit changes to git log with a helpful message
git push origin main # Push changes to our public remote so we can submit!
```

### Thinking Question

- Can you look at the diagram above with confidence now?
