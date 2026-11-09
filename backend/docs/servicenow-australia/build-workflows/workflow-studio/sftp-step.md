---
title: SFTP step
description: Create a reusable action to manage files and directories on an SFTP server and to move files from one SFTP server to another.
locale: en-US

release: australia
product: Workflow Studio
classification: workflow-studio
topic_type: reference
last_updated: "2026-03-12"
reading_time_minutes: 2
breadcrumb: [Steps, Flows, subflows, and actions reference, Flows, subflows, and actions, Workflow Studio, Build workflows]
---

# SFTP step

Create a reusable action to manage files and directories on an SFTP server and to move files from one SFTP server to another.

**Note:**

-   This step requires an Integration Hub subscription. For more information, see [Legal schedules - IntegrationHub overview]([external reference omitted]). For more information about the ServiceNow® Integration Hub subscription packages, see [Integration Hub usage and subscription]([external reference omitted]). After the required plugin is activated, the step is visible under Integrations.
-   The SFTP step runs only on a ServiceNow® MID Server with SSH capabilities. Activate the plugin, Integration Hub in Workflow Data Fabric Professional \(com.glide.hub.integrations.professional\) to use the JDBC capability for the MID Server. For more information, see [Request an Integration Hub plugin]([external reference omitted]).
-   The SFTP step requires a credential record that supports either SSH private key credentials or SSH credentials. This step does not support Windows credentials where the **Use MID Server service account** option is selected.

## Roles and availability

The SFTP step is available as an Workflow Studio action step. Users with the action\_designer role can create a custom action with one or more action steps.

## Prerequisite

Activate the Managed File Transfer Extensions for the SFTP Step \(com.glide.hub.action\_step.sftp\_mft\) plugin.

## SFTP commands

-   [Copy File]([external reference omitted])
-   [Copy Directory]([external reference omitted])
-   [Create Directory]([external reference omitted])
-   [Get File List]([external reference omitted])
-   [Remove File]([external reference omitted])
-   [Remove Files]([external reference omitted])
-   [Delete Directory]([external reference omitted])
-   [Rename File or Directory]([external reference omitted])
-   [Set File Attributes]([external reference omitted])
-   [Copy Attachments To SFTP Server]([external reference omitted])
-   [Copy Files To This Instance]([external reference omitted])

**Note:** The SFTP commands can be performed on a maximum of 10,000 files at a time.

-   **[Copy File]([external reference omitted])**  
Copies a file from the source SFTP server to target SFTP server.
-   **[Copy Directory]([external reference omitted])**  
Copies a directory from the source SFTP server to the target SFTP server.
-   **[Create Directory]([external reference omitted])**  
Creates a new directory on an SFTP server.
-   **[Get File List]([external reference omitted])**  
Returns a list of files from a given directory and its subfolders on an SFTP server.
-   **[Remove File]([external reference omitted])**  
Removes a file on an SFTP server, including subfolders, when configured.
-   **[Remove Files]([external reference omitted])**  
Remove files on an SFTP server, including subfolders, when configured.
-   **[Delete Directory]([external reference omitted])**  
Deletes directory on an SFTP server, including subfolders, when configured.
-   **[Rename File or Directory]([external reference omitted])**  
Renames a file or directory on an SFTP server.
-   **[Set File Attributes]([external reference omitted])**  
Sets common file attributes, such as timestamps, size, permissions, and UID/GID, for a file or directory on an SFTP server.
-   **[Copy Attachments To SFTP Server]([external reference omitted])**  
Copies the specified attachments from ServiceNow instance to an SFTP server.
-   **[Copy Files To This Instance]([external reference omitted])**  
Attaches the specified files in the SFTP server to the specified record in ServiceNow instance.

**Parent Topic:**[Workflow Studio steps]([external reference omitted])

