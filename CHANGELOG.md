# v0.4.2
## Improves
- Change the `VerticalScroll` bar width of the `details` screen to 1, make the vertical scrollbar style of the modal look better.

# v0.4.1

## Bug Fixes
- Fixed: crash when tree-sitter is not installed or when editing documents of unknown format. 
> Textual requires tree-sitter >= 0.25.0 which dropped support for Python 3.9. The TextArea falls back to plain text by design, rather than crashing programs where tree-sitter can't be installed.


# v0.4.0
## New Features

- Remove the fuzzy match(search) function for already loaded resources.
- Added support for using the `label_selector` and `field_selector` fields to retrieve resources from the Kubernetes API, enabling structured filtering of fields.

## Improves
- When the resource obtained from the Kubernetes API is empty or the filter result is empty, display a prompt and inform the user of the current namespace and filter conditions (if exist).

## Bug Fixes

- Fixed TypeError: unsupported operand type(s) for |: 'type' and 'type' in Python3.9
- Fixed Textarea widget lost syntax highlighting

# v0.3.1


# v0.3.0
## New Features

- Transfer files beteewn local and pod

## Bug fixes

- fixed Kubernetes Client v36.0.0 where the read_namespaced_pod_log function did not support the watch parameter.

## Docs

- Update on the introduction and usage of transfer files
