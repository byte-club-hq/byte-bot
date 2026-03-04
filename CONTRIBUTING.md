# Contributing to byte-bot

Thank you for considering contributing!
This is a project specifically geared toward collaboration and learning, so human derived contributions of all kinds are welcome.

## Code of Conduct

This project is by learners, for learners. Because this is a training ground, the process is more important than the result.

- **Do the work yourself:** While AI and documentation are great tutors to help you understand a concept, please avoid vibe coding.
- **Human-Vetted Content:** You are responsible for every line of code you submit. If you use AI to help you, you must be able to explain the logic during a code review.

<!-- omit in toc -->
## Table of Contents

- [Join The Community](#join-the-community)
- [I Have a Question](#i-have-a-question)
- [I Want To Contribute](#i-want-to-contribute)
  - [Your First Code Contribution](#your-first-code-contribution)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Improving The Documentation](#improving-the-documentation)
- [Styleguides](#styleguides)
- [Commit Messages](#commit-messages)


## Join The Community
In anticipation of AI agents flooding the repository with pull requests (as well as the influx of vibe coded contributions in many open source projects) we have limited contributions to be from members of the byte-club organization.
If you wish to contribute to the repository, feel free to join the byte-club [Discord server](https://discord.com/invite/cAtAdY2CCf) and personally ask a project lead to add you to the organization.

## Suggesting Enhancements and Asking Questions

The intended channel for discourse and questions about the project is the Discord server. We have forum channels dedicated for this purpose.

## I Want To Contribute

> ### Legal Notice <!-- omit in toc -->
> When contributing to this project, you must agree that you have authored 100% of the content, that you have the necessary rights to the content and that the content you contribute may be provided under the project licence.

### Reporting Bugs

<!-- omit in toc -->
#### Before Submitting a Bug Report

We ask you to investigate carefully, collect information and describe the issue in detail in your report. Please complete the following steps in advance:

- Make sure that you are using the latest version.
- Determine if your bug is really a bug and not an error on your side e.g. using incompatible environment components/versions (Make sure that you have read the [documentation](#improving-the-documentation)).
- To see if other users have experienced (and potentially already solved) the same issue you are having, check if there is not already a bug report existing for your bug or error in the [bug tracker](https://github.com/byte-club-hq/byte-bot/issues?q=label%3Abug).
- Also make sure to search the internet (including Stack Overflow) to see if users outside of the GitHub community have discussed the issue.
- Collect information about the bug:
  - Stack trace (Traceback)
  - OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
  - Version of the interpreter, compiler, SDK, runtime environment, package manager, depending on what seems relevant.
  - Possibly your input and the output
  - Can you reliably reproduce the issue? And can you also reproduce it with older versions?

<!-- omit in toc -->
#### How Do I Submit a Good Bug Report?

> You must never report security related issues, vulnerabilities or bugs including sensitive information to the issue tracker, or elsewhere in public. Instead sensitive bugs must be DM'ed to one of the project leads.

We use GitHub issues to track bugs and errors. If you run into an issue with the project:

- Open an [Issue](https://github.com/byte-club-hq/byte-bot/issues/new). (Since we can't be sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and not to label the issue.)
- Explain the behavior you would expect and the actual behavior.
- Please provide as much context as possible and describe the *reproduction steps* that someone else can follow to recreate the issue on their own. This usually includes your code. For good bug reports you should isolate the problem and create a reduced test case.
- Provide the information you collected in the previous section.

Once it's filed:

- The project team will label the issue accordingly.
- A team member will try to reproduce the issue with your provided steps. If there are no reproduction steps or no obvious way to reproduce the issue, the team will ask you for those steps and mark the issue as `needs-repro`. Bugs with the `needs-repro` tag will not be addressed until they are reproduced.
- If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as possibly other tags (such as `critical`), and the issue will be left to be [implemented by someone](#your-first-code-contribution).

<!-- omit in toc -->
#### Enhancement Suggestions

Enhancement suggestions are tracked as [GitHub issues](https://github.com/byte-club-hq/byte-bot/issues).
- Make sure that you are using the **latest version**.
- **Read the documentation** carefully and find out if the functionality is already covered, maybe by an individual configuration.
- Perform a [search](https://github.com/byte-club-hq/byte-bot/issues) to see if the enhancement has **already been suggested**. If it has, add a comment to the existing issue instead of opening a new one.
- Find out whether your idea **fits with the scope** and aims of the project. It's up to you to make a strong case to convince the project's developers of the merits of this feature.

When writing an enhancement suggestion, please:
- Use a **clear and descriptive title** for the issue to identify the suggestion.
- Provide a **step-by-step description of the suggested enhancement** in as many details as possible.
- **Describe the current behavior** and **explain which behavior you expected to see instead** and why. At this point you can also tell which alternatives do not work for you.
- You may want to **include screenshots or screen recordings** which help you demonstrate the steps or point out the part which the suggestion is related to. You can use [LICEcap](https://www.cockos.com/licecap/) to record GIFs on macOS and Windows, and the built-in [screen recorder in GNOME](https://help.gnome.org/users/gnome-help/stable/screen-shot-record.html.en) or [SimpleScreenRecorder](https://github.com/MaartenBaert/ssr) on Linux. <!-- this should only be included if the project has a GUI -->
- **Explain why this enhancement would be useful** to most byte-bot users. You may also want to point out the other projects that solved it better and which could serve as inspiration.

### Your First Code Contribution
Please refer to the [README](https://github.com/byte-club-hq/byte-bot/blob/main/README.md) for setting up the codebase locally.

To simulate a professional environment, we follow a strict issue-first workflow:

1. **Find an Issue:** Browse the issues and find one geared toward your skill level.
2. **Claim It:** Leave a comment on the issue so the team knows you are working on it.
  - Branching: Create a branch relative to that ticket name/number.
  - Format: issue-[number] or issue-[number]-description
    - Example: git checkout -b issue-1-login-fix
3. **Work & Test:** Implement your changes, ensuring you follow our Styleguides.
4. **Submit a PR:** Be descriptive in your Pull Request. Explain what you changed and why.

### Improving The Documentation
Right now, documentation is maintained in the form of python docstrings.
Docstrings are meant to be maintained in parallel with the code, but if you notice that an improvement can be made to the documentation, feel free to open an enhancement issue.

## Styleguides
### Code Standards
In a large team, code is read 10x more often than it is written. We prioritize readability over cleverness.
- **Code should be mostly self documenting:** Under 95% of circumstances, it should be clear what your code does by looking at it.
  You can accomplish this by using descriptive and precise variable names, conserving [cyclomatic complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity) and proper seperation of concerns.
- **Comments should be used when intent is unclear:** Even if your code itself is readable, you should include comments especially when its reasoning is invisible (i.e. workarounds/hacks, magic numbers, regex, performance optimizations, etc.).
- **Limit vagueness to idiomatically universal contexts:** For extremely limited scopes like loop counters (`for i in range(10)` where `i` is short for `index`) or list comprehensions, mathematical formulas or coordinates (`x`, `y`, & `z` as coordinate variables), and lambda functions, it may actually benefit code readability to be vague with variable names.

### Commit Messages
In general, we try to adhere to the [Conventional Commit Specification](https://www.conventionalcommits.org/en/v1.0.0/). Please refer to it for more detail.
To simulate a professional environment, please write commit messages in the imperative mood ("Fix" instead of "Fixed") and if you wish to include a commit body along with your summary, seperate it with a blank line:

```
feat: add email notifications for new direct messages

This change implements a new notification system to alert users of 
incoming direct messages, improving user engagement. The previous system
did not have any real-time notification mechanism.
```
