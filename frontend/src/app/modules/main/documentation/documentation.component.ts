import { ChangeDetectionStrategy, Component, ViewEncapsulation } from '@angular/core'
import { InnerHTMLExternalLinksDirective, InnerHTMLImageOverlayDirective, SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-documentation',
  templateUrl: './documentation.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [InnerHTMLExternalLinksDirective, InnerHTMLImageOverlayDirective, MaterialImports, SharedImports],
})
export class DocumentationComponent {
  readonly faq: { category: string; faqs: { question: string; answer: string }[] }[] = [
    {
      category: 'Features',
      faqs: [
        {
          question: 'How can I get general information about the capabilities, features, and active development of SEED?',
          answer: `
            <ul>
              <li>For a list of new features and fixed capabilities, visit the <a href="https://github.com/SEED-platform/seed/releases">SEED Platform GitHub Releases</a> page.</li>
              <li>Consult the <a href="https://seed-platform.org/references/">Reference Page</a> for publications related to SEED. Additionally, this paper describes the BuildingSync® format which can be used to import data into the SEED Platform:
                <blockquote>DeGraw, Jason, Kristin Field-Macumber, Nicholas Long, and Supriya Goel. 2018. <a href="https://buildingsync.net/static/documents/DeGraw-ACEEE-BuildingSync-in-Action.pdf">“BuildingSync® in Action : Example Implementations.”</a> In 2018 ACEEE Summer Study on Energy Efficiency in Buildings, 1–12. Pacific Grove, CA.</blockquote>
              </li>
              <li>Here are some related projects that are using SEED:
                <ul>
                  <li><a href="https://neep.org/solutions-low-carbon-states-and-communities/beam-building-energy-analysis-manager">Building Energy Analysis Manager (BEAM)</a></li>
                  <li><a href="https://www.aceee.org/files/proceedings/2018/assets/attachments/0194_0286_000247.pdf">The BayREN Integrated Commercial Retrofits (BRICR) Project</a> and <a href="https://www.energy.gov/sites/prod/files/2018/05/f52/24293_Hooper_050318-900.pdf">BRICR Presentation</a></li>
                  <li><a href="https://www.energy.gov/cmei/buildings/energy-data-vault">The Energy Data Vault (EDV) Project</a></li>
                </ul>
              </li>
            </ul>`,
        },
        {
          question:
            'Do you anticipate any SEED issues if there are irregular data updates for each building? For example, with a point-of-sale benchmarking program, building data would only be updated when a property is sold.',
          answer:
            'There should not be any issues importing data at non-regular times; users frequently do so with ENERGY STAR Portfolio Manager data.',
        },
        {
          question: 'The linking feature is new - can I get more details on how it works?',
          answer: `
            <p>Cross-cycle linking, or simply <strong>linking</strong>, allows organizations to analyze uploads of the same property (or tax lot) over time. This is done by matching records in one cycle with records within other cycles. SEED builds these associations automatically during import using matching criteria as specified by the organization. Additionally, this association can be made during a manual edit to record values (especially if the changed value is a matching criteria field).</p>
            <p>For even more details on matching and linking, refer to <a href="https://github.com/SEED-platform/seed/blob/develop/docs/source/matching.rst#linking-across-cycles">this section of the matching, merging, and linking documentation</a>.</p>`,
        },
        {
          question: 'How does linking interact with paired properties and tax lots?',
          answer:
            'At the moment, paired property and tax lot relationships are displayed and managed separately from linked relationships. That is, paired records are viewed and managed in a separate area of SEED as linked records.',
        },
        {
          question:
            'Mapping, Merging, Matching, Pairing, and Linking - What do each of those mean and how are they related or different from each other?',
          answer: `
            <p>Different inventory management and analysis features in SEED are based on the relationships between records of different inventory types (properties and tax lots). Those terms help describe these relationships.</p>
            <img class="drop-shadow-lg" src="images/documentation/features/mapping-diagram.webp" alt="Mapping diagram, description follows">
            <ul>
              <li><strong>Mapping</strong> refers to the process of mapping newly imported data fields to the known database column names in order to create a record.</li>
              <li><strong>Merging</strong> refers to the act of combining multiple properties (or multiple tax lots) into one record. This can be done manually by users or automatically by SEED and helps avoid duplicate records.</li>
              <li><strong>Matching</strong> refers to whether two or more properties match (or two or more tax lots). A match can only happen if specific fields between records match. Records can be compared within the same cycle (triggering a merge) or across cycles (building a link). The specific fields can be modified for each organization.</li>
              <li><strong>Pairing</strong> refers to the association between properties and tax lots within the same cycle.</li>
              <li><strong>Linking</strong> refers to the association between properties across cycles (or tax lots across cycles) and is useful for analysis.</li>
            </ul>
            <p>For more details, refer to <a href="https://github.com/SEED-platform/seed/blob/develop/docs/source/matching.rst">this documentation that covers matching, merging, and linking</a>.</p>`,
        },
        {
          question: 'I just geocoded my data using SEED. How do I review and verify the results?',
          answer:
            'There are multiple ways of verifying geocoding results. The most obvious way is to verify that latitude and longitude fields are populated. Additionally, SEED provides a field called "Geocoding Confidence". This field can provide evidence of how the geocoding went for that record - a value starting with "Low..." indicates that geocoding failed for a record because the address values didn\'t yield reliable results. Finally, SEED provides an inventory map page that allows you to view where the points are located on a map.',
        },
        {
          question: 'When and how does SEED geocode my data?',
          answer: `
            <p>SEED will attempt to geocode your data with latitude and longitude values only if the following are true:</p>
            <ol>
              <li>Your organization has a MapQuest API key. You can register for one through MapQuest's website and apply it on your organization settings page.</li>
              <li>The records being geocoded have address values that can be read by SEED. In your organization column settings page, you can specify which fields and in what order SEED will use to build the full address that will be geocoded by MapQuest.</li>
              <li>The records being geocoded do not already have latitude and longitude populated. SEED won't override these values, but you can edit and remove these values if you want SEED to attempt to generate them with MapQuest.</li>
            </ol>
            <p>SEED will make this attempt in the following cases:</p>
            <ul>
              <li>During the file import process, after you've mapped columns, SEED will automatically attempt geocoding on records.</li>
              <li>On either the properties page or the tax lots page, you can select records and use the "Geocode Selected" button under the Actions menu.</li>
            </ul>
            <p>Note: Valid UBID (properties or tax lots) values can be parsed to provide a latitude and longitude value. On import, UBID is used instead of MapQuest if available. On the inventory pages, there's a separate Action menu button to "Decode UBID for Selected".</p>`,
        },
      ],
    },
    {
      category: 'General',
      faqs: [
        {
          question: 'What resources or support do you provide to jurisdictions interested in using SEED as part of a benchmarking program?',
          answer:
            'We typically provide technical support as needed and within reason. As the community grows, there are more users able to provide support. It is recommended to use <a href="https://github.com/SEED-platform/seed/issues">GitHub issues</a> to a) view existing feature requests and issues, and b) communicate with various developers.',
        },
      ],
    },
    {
      category: 'Hosting',
      faqs: [
        {
          question: 'What is the estimated cost to implement and maintain the SEED Platform as part of a benchmarking system?',
          answer: `
            <p>There are three hosting options:</p>
            <ol>
              <li>Self-hosting on user-owned hardware</li>
              <li>Self-hosting on the cloud (e.g., Amazon, Google Compute)</li>
              <li>Paying a hosting provider. Several companies offer SEED as a hosted solution:
                <ul>
                  <li><a href="https://clearlyenergy.com/">ClearlyEnergy</a></li>
                  <li><a href="https://www.earthadvantage.org/">Earth Advantage</a></li>
                  <li><a href="https://opentech.eco/">OPEN Technologies</a></li>
                  <li><a href="https://psdconsulting.com/">PSD</a></li>
                </ul>
                <p>See the <a href="https://seed-platform.org/technical_ally/">Technical Allies page</a> for more information.</p>
              </li>
            </ol>
            <p>Options (1) and (2) are highly dependent on internal expertise and potential requirements related to sharing outside of a user's organization. Generally, cloud hosting simplifies management of networks, hardware, firewalls, and backups. An example SEED instance hosted in the cloud with staging and production environments costs approximately $1,000 to $1,500 per month for a large instance capable of processing records for an entire region.</p>`,
        },
        {
          question:
            'Can the web interface of a self-hosted SEED instance be accessed via a local network, or is internet access required? Can access via local internet be disabled?',
          answer:
            "Access via public internet would be a function of the self-hosted instance's network configuration. If SEED is hosted on Amazon Web Services, for example, the host can deny access based on CIDR blocks (IP address ranges) in the Amazon Web Services Console. If the application is hosted on user-owned infrastructure, a local firewall can prevent external access. Note that internal access in both cases would still be available (i.e., the web interface would be accessible).",
        },
      ],
    },
    {
      category: 'Industry Involvement',
      faqs: [
        {
          question:
            'Do any applications use SEED to store and analyze building construction permit applications for energy code compliance?',
          answer:
            'We are not aware of any applications which use SEED to do this, although SEED could be linked to another tool, like SalesForce. We recommend contacting Earth Advantage and Clearly Energy for more details (see the <a href="https://seed-platform.org/technical_ally/">Technical Allies page</a>).',
        },
        {
          question: 'Are there any organizations that are developing free and open-source plug-ins for SEED?',
          answer: `
            <p>You can find more information about organizations contributing to SEED Platform development below:</p>
            <ul>
              <li><a href="https://www.energy.gov/cmei/buildings/seed-platform-collaborative">SEED Platform Collaborative</a></li>
              <li><a href="https://github.com/SEED-platform/seed/blob/develop/AUTHORS.md">SEED Platform Contributing Developers</a></li>
              <li><a href="https://seed-platform.org/technical_ally/">SEED Technical Allies</a></li>
              <li><a href="https://www.energy.gov/sites/prod/files/2018/05/f52/24293_Hooper_050318-900.pdf">BayREN Integrated Commercial Retrofits (BRICR)</a></li>
              <li><a href="https://www.energy.gov/cmei/buildings/energy-data-vault">Energy Data Vault (EDV)</a></li>
            </ul>`,
        },
      ],
    },
    {
      category: 'Security',
      faqs: [
        {
          question: 'Can you suggest any encryption solutions, since the SEED software does not encrypt its database?',
          answer:
            'We recommend hard drive encryption of the database server as the easiest solution; encrypting locally is more complicated but certainly doable.',
        },
        {
          question: 'How does SEED secure internet data communications?',
          answer:
            'Secure sockets layer (SSL) protocols must be configured on the hosted instance. This requires purchasing and adding certificates to the deployed server, or using a third-party service (e.g., CloudFlare or Cloudfront) to manage the domain name system (DNS) and the SSL certificates.',
        },
      ],
    },
  ]
}
