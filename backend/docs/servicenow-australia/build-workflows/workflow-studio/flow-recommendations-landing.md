---
title: Flow recommendations
description: Select the next component in your flow from a list of AI-generated recommendations.
locale: en-US

release: australia
product: Workflow Studio
classification: workflow-studio
topic_type: reference
last_updated: "2026-03-12"
reading_time_minutes: 3
breadcrumb: [Build flows, Flows, subflows, and actions, Workflow Studio, Build workflows]
---

# Flow recommendations

Select the next component in your flow from a list of AI-generated recommendations.

## Get started

<table id="table_t25_zqk_1gc" class="nav-card presentation"><tbody><tr><td>

[Explore\[Omitted image "bus-explore.svg"\] Alt text:Learn about flow recommendations]([external reference omitted])

</td><td>

[Configure\[Omitted image "bus-sdlc.svg"\] Alt text:Activate the ServiceNow Otto for Creator plugin and the flow recommendations skill]([external reference omitted])

</td></tr><tr><td>

[Generate\[Omitted image "bus-start-developing.svg"\] Alt text:Create a flow using ServiceNow Otto for Creator]([external reference omitted])

</td><td>

[Reference\[Omitted image "bus-learn.svg"\] Alt text:Get details about ServiceNow Otto for Creator roles]([external reference omitted])

</td></tr></tbody>
</table>**Important:**

-   Not all model providers are available for customers with in-country SKUs, and some AI products/features are currently unavailable for in-country customers. For more information, see the [KB1584492]([external reference omitted]) article in the Now Support Knowledge Base. Be sure to check for model provider availability updates in future releases.
-   Some AI products/features are currently unavailable for customers in the FedRAMP, NSC DOD IL5, or Australia IRAP-Protected data centers, self-hosted customers, or in other restricted environments. For more information, see the [KB0743854]([external reference omitted]) article in the Now Support Knowledge Base. Be sure to check for availability updates in future releases.
-   Some AI products/features are currently available only for customers in some regions. Be sure to check for availability updates in future releases.
-   Some AI products and skills are not available in Regulated Markets. For more information, see [KB2593939: Regulated Markets AI Products/Skills Not Available]([external reference omitted]). Be sure to check for availability updates in future releases.

**Important:** Some AI products/features are currently unavailable for customers in the FedRAMP, NSC DOD IL5, or Australia IRAP-Protected data centers, self-hosted customers, or in other restricted environments. For more information, see the [KB0743854]([external reference omitted]) article in the Now Support Knowledge Base. Be sure to check for availability updates in future releases.

**Important:** Some generative AI skills, agents, and agentic workflows are turned on by default. The default behavior works as follows:

-   **New customers**

    When you install an AI product, designated generative AI skills, AI agents, or agentic workflows are turned on automatically.

-   **Existing customers who are upgrading \(starting with Zurich Patch 4\)**

    There is no change to skills, agents, or agentic workflows that are currently enabled and customized.

    An AI asset is turned on if:

    -   The AI plugin is installed, but the asset was never turned on.
    -   An admin has never adjusted roles for the skill.
    An AI asset is not turned on if:

    -   The asset was previously turned on, and then turned off again.
    -   An admin has adjusted roles for the asset.

For more information, see [AI agents, skills, and agentic workflows on by default]([external reference omitted]).

## AI limitations

This application uses artificial intelligence \(AI\) and machine learning, which are rapidly evolving fields of study that generate predictions based on patterns in data. As a result, this application may not always produce accurate, complete, or appropriate information. Furthermore, there is no guarantee that this application has been fully trained or tested for your use case. To mitigate these issues, it is your responsibility to test and evaluate your use of this application for accuracy, harm, and appropriateness for your use case, employ human oversight of output, and refrain from relying solely on AI-generated outputs for decision-making purposes. This is especially important if you choose to deploy this application in areas with consequential impacts such as healthcare, finance, legal, employment, security, or infrastructure. You agree to abide by [ServiceNow’s AI Acceptable Use Policy]([external reference omitted]), which may be updated by ServiceNow.

## Data processing

This application requires data to be transferred from ServiceNow customers' individual instances to a centralized ServiceNow environment, which may be located in a different data center region from the one where your instance is, and potentially to a third-party cloud provider, such as Microsoft Azure. This data is handled per ServiceNow's internal policies and procedures, including our policies available through our [CORE Compliance Portal]([external reference omitted]).

-   **[Exploring Flow recommendations]([external reference omitted])**  
Select the next component in your flow from a list of AI-generated recommendations. The system generates recommendations based on the current position in the flow and the flow component names listed before.
-   **[Turn on the flow recommendations skill]([external reference omitted])**  
Turn on the flow recommendations skill to get recommendations for the next step of your flow with generative AI.

**Parent Topic:**[Building flows]([external reference omitted])

