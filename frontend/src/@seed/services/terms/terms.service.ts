import { inject, Injectable } from '@angular/core'
import { ConfirmationService } from '../confirmation'

const NLR_TERMS_ACCEPTED_AT_KEY = 'nlrTermsAcceptedAt'
const NLR_TERMS_ACCEPTANCE_DAYS = 90
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000

@Injectable({ providedIn: 'root' })
export class TermsService {
  private _confirmationService = inject(ConfirmationService)

  hasAcceptedTerms(email: string): boolean {
    const key = `${NLR_TERMS_ACCEPTED_AT_KEY}:${email.toLowerCase().trim()}`
    const acceptedAt = Number(localStorage.getItem(key))
    const acceptanceAge = Date.now() - acceptedAt

    return (
      Number.isFinite(acceptedAt)
      && acceptedAt > 0
      && acceptanceAge >= 0
      && acceptanceAge < NLR_TERMS_ACCEPTANCE_DAYS * MILLISECONDS_PER_DAY
    )
  }

  recordTermsAcceptance(email: string): void {
    const key = `${NLR_TERMS_ACCEPTED_AT_KEY}:${email.toLowerCase().trim()}`
    localStorage.setItem(key, Date.now().toString())
  }

  showTermsOfService(): void {
    this._confirmationService.open({
      title: 'DOE Standard Energy Efficiency Data Platform | NLR Data Terms',
      message: `<div class="prose h-160 max-h-[calc(100svh-280px)] overflow-auto sm:-mr-10 sm:pr-10 mt-4 max-w-none">
         <p>You, and your company or organization (the <strong>PROVIDER</strong>) have agreed to upload and provide <strong>PROPRIETARY DATA</strong>, including energy efficiency data, building data, and building energy performance data to the Standard Energy Efficiency Data (SEED™) Platform database that the U.S. Department of Energy (the Government) and Alliance for Energy Innovation, LLC (“Alliance”) the manager and operator of the National Laboratory of the Rockies (“NLR”) (the <strong>RECIPIENT</strong>) have created and provide for use for registered users.</p>
         <p><strong>PROPRIETARY DATA</strong> is defined as follows:</p>
         <p>(a) information that embody trade secrets or commercial or financial information that is confidential and privileged; (b) information that is confidential and privileged and developed at private expense (i.e., not with Federal funds); (c) information that is not customarily released to the public; and/or (d) information whose disclosure to the public could result in financial harm to the PROVIDER, to owners of buildings whose information is contained in the PROPRIETARY DATA, or to other stakeholders.</p>
         <p>In order to upload PROPRIETARY DATA, you will be required to create an account and provide the RECIPIENT with a username, password, and email address. You are solely responsible for maintaining the confidentiality of the password and username you provided during the registration process and are fully responsible for all activities that occur under your password or account.</p>
         <p>The PROPRIETARY DATA shall remain protected until the PROVIDER provides notice of termination of their account on the SEED Platform and provides notice to remove PROPRIETARY DATA from the SEED Platform database, at which time the RECIPIENT will promptly return and/or destroy the PROPRIETARY DATA uploaded in the SEED Platform database.</p>
         <p>By providing the PROPRIETARY DATA, PROVIDER agrees to the following:</p>
         <ol>
           <li>PROVIDER has the authority to provide the PROPRIETARY DATA to the RECIPIENT, that the information provided constitutes PROPRIETARY DATA, and consents to the information provided being labeled and treated as PROPRIETARY DATA. If PROVIDER wishes to provide non-proprietary data, please contact <a href="mailto:BTODataTools@ee.doe.gov">BTODataTools@ee.doe.gov</a>.</li>
           <li>RECIPIENT may host, display, and manage such PROPRIETARY DATA for the PROVIDER and the Government to access, analyze, and manage through the SEED Platform.</li>
           <li>RECIPIENT may use, view, or duplicate the PROPRIETARY DATA and may share the PROPRIETARY DATA with support services contractors within the scope of their contracts. RECIPIENT may share the PROPRIETARY DATA to other DOE National Laboratories participating in the SEED Platform project, under the restriction that (i) the PROPRIETARY DATA be retained in confidence and not be further disclosed, (ii) the PROPRIETARY DATA will be destroyed when the DOE National Laboratory’s participation in the SEED Platform has ended.</li>
         </ol>
       </div>`,
      width: 'wide',
      icon: {
        show: true,
        name: 'fa-solid:file-contract',
        color: 'primary',
      },
      actions: {
        confirm: {
          show: false,
          label: 'Close',
          color: 'accent',
        },
        cancel: {
          show: true,
          label: 'Close',
        },
      },
      dismissible: true,
    })
  }
}
