---
title: Transform functions
description: Transform data pill values without the need to write a script. Use transform functions to reformat text, perform mathematical calculations, sanitize potentially unsafe SQL statements, and serialize complex objects to raw XML.
locale: en-US

release: australia
product: Workflow Studio
classification: workflow-studio
topic_type: concept
last_updated: "2026-03-12"
reading_time_minutes: 6
breadcrumb: [Flows, subflows, and actions reference, Flows, subflows, and actions, Workflow Studio, Build workflows]
---

# Transform functions

Transform data pill values without the need to write a script. Use transform functions to reformat text, perform mathematical calculations, sanitize potentially unsafe SQL statements, and serialize complex objects to raw XML.

Available transform function categories include [date and time]([external reference omitted]), [string]([external reference omitted]), [utilities]([external reference omitted]), [simple math]([external reference omitted]), [sanitize shell arguments]([external reference omitted]), [sanitize SQL]([external reference omitted]), and [complex data]([external reference omitted]). Some examples of transform function uses include:

-   Trimming white space from a string before integrating it into the CMDB.
-   Adding days, hours, minutes, and seconds to a date or time to localize for a specific time zone.
-   Sanitizing SQL values to prevent injection as part of a [JDBC step]([external reference omitted]) for an Integration Hub spoke.
-   Retrieving an appropriate value from a map of priorities that have equivalent values in a third-party database.
-   Transforming a complex object into raw XML as part of a [REST step]([external reference omitted]) **Request Body** field.

**Note:** Custom transform functions are not currently supported. For information on creating custom functions to transform Workflow Studio data, see [Inline scripts]([external reference omitted]).

## Applying a transform function

You can apply a transform function to a data pill when you are designing or creating a flow. To apply a transform function, point or tab to a data pill and select the **f\(x\)** \(\[Omitted image "fx-icon.png"\] Alt text: function icon\) icon that appears. Selecting the icon displays the Available Transforms list. Select the transform function that you want to apply to your data pill, enter information into any required fields, and select **Apply**. Your selected transform function appears in the Applied Transforms list.

\[Omitted image "apply-transform-function-orlando.gif"\] Alt text: Applying a transform function to a data pill.

## Applying multiple transform functions

You can apply multiple transform functions to the same data pill. The system applies transform functions sequentially from top to bottom as listed in the Applied Transforms list. For example, you can apply a String to Date transform function followed by the Add Time transform function.

## Viewing applied transform functions

You can find out which transform functions are applied to a data pill by looking at the Applied Transforms list. When you are designing or creating a flow or action, point to or tab into the data pill and select the **f\(x\)** \(\[Omitted image "fx-applied-icon.png"\] Alt text: function icon selected\) icon. You can also view applied transform functions in the [flow execution details]([external reference omitted]).

**Note:** The output values for applied transform functions are field values, not [Display values]([external reference omitted]).

When a data pill is dropped into certain types of inputs, the system automatically suggests a transform function category that is related to the input. For example, the system suggests transform functions to escape special characters in SQL statements, prevent script injection in shell scripts, and validate API or operation requests. Currently, the system suggests transform function categories for these inputs:

-   For data pills dropped in the JDBC step's **SQL Statement** input, the [sanitize SQL transform function category]([external reference omitted]) is displayed automatically.
-   For data pills dropped in the SSH step's **Command** input, the [sanitize shell arguments transform function category]([external reference omitted]) is displayed automatically.

## General guidelines

-   **Apply transform functions to valid types of data pills for the input**

    Be sure to check the type of data pill for the input before applying a transform function. Applying a transform function to an invalid data pill type results in the system skipping the transform. An error also occurs if transform functions produce results that the system cannot parse. For example, when transforming a string into a date, the system throws an error if the transform does not produce a valid date.

-   **Confirm applied transform functions for multiple inputs with the same data pill**

    A transform function creates a new value at runtime for a specific input, and does not change the original data pill. If you use the same data pill across multiple actions or steps, transform functions must therefore be applied to each individual input.

-   **View final transformed values in the flow execution details**

    Only the final transformed value appears in the [flow execution details](), and not the value for each applied transform.

-   **Test transform functions to verify they produce expected results**

    Make sure that your transform functions produce the expected runtime values for the data pills. For more information, see [Test a flow]([external reference omitted]) and [Test an action]([external reference omitted]).


-   **[Date and time transform functions]([external reference omitted])**  
Use date and time transform functions to recalculate or reformat data pills for Date/Time values.
-   **[String transform functions]([external reference omitted])**  
Use string transform functions to reformat or perform calculations on String data pills.
-   **[Utilities transform functions]([external reference omitted])**  
Use utilities transform functions to return a Complex Object from an Array, or a value associated with a specific key.
-   **[Simple math transform functions]([external reference omitted])**  
Use simple math transform functions to perform basic mathematical calculations on Number data pills.
-   **[Sanitize shell arguments transform functions]([external reference omitted])**  
Use sanitize shell arguments transform functions to remove any potentially unsafe command injections in String data pills to be used for Bash shell scripting.
-   **[Sanitize SQL transform functions]([external reference omitted])**  
Use sanitize SQL transform functions to escape special characters and prevent injection in String data pills to be used for SQL statements.
-   **[Complex data transform functions]([external reference omitted])**  
Use complex data transform functions to serialize Complex Object data pills into an XML format.

**Parent Topic:**[Flows, subflows, and actions reference]([external reference omitted])

