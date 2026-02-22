import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import JsonPanel from '../components/JsonPanel'
import ResourceTable from '../components/ResourceTable'
import StatusPill from '../components/StatusPill'
import SupportedActions from '../components/SupportedActions'
import { useClient } from '../state/ClientContext'
import type { ODataLink, RedfishResource } from '../types/redfish'
import {
  extractSupportedActions,
  formatIsoDate,
  getStatusTone,
  isODataLink,
  resourceDisplayName,
  toODataPath,
} from '../utils/redfish'

interface JobDocumentField {
  name: string
  dataType: string
  required: boolean
  allowableValues: string[]
  valueHint: string
  description?: string
}

interface JobSummary {
  id: string
  name: string
  state: string
  status: string
  percentComplete: number | null
  createdAt?: string
  startTime?: string
  uri: string
  raw: RedfishResource
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function readString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim().length > 0 ? value : undefined
}

function toDocumentFields(resource: RedfishResource): JobDocumentField[] {
  if (!Array.isArray(resource.ParameterMetadata)) {
    return []
  }

  const fields: JobDocumentField[] = []

  resource.ParameterMetadata.forEach((parameter, index) => {
    if (!isRecord(parameter)) {
      return
    }

    const name = readString(parameter.Name) ?? `Field${index + 1}`
    const dataType = readString(parameter.DataType) ?? 'String'
    const required = typeof parameter.Required === 'boolean' ? parameter.Required : false
    const allowableValues = Array.isArray(parameter.AllowableValues)
      ? parameter.AllowableValues.map((value) => String(value))
      : []
    const valueHint = parameter.ValueHint === undefined || parameter.ValueHint === null ? '' : String(parameter.ValueHint)
    const description = readString(parameter.Description)

    fields.push({
      name,
      dataType,
      required,
      allowableValues,
      valueHint,
      description,
    })
  })

  return fields
}

function buildDefaultValues(fields: JobDocumentField[]): Record<string, string> {
  const values: Record<string, string> = {}

  fields.forEach((field) => {
    if (field.valueHint.length > 0) {
      values[field.name] = field.valueHint
      return
    }

    if (field.allowableValues.length > 0) {
      values[field.name] = field.allowableValues[0]
      return
    }

    values[field.name] = ''
  })

  return values
}

function findSubmitJobActionTarget(resource: RedfishResource): string | undefined {
  if (!isRecord(resource.Actions)) {
    return undefined
  }

  const submitAction = resource.Actions['#JobDocument.SubmitJob']
  return isRecord(submitAction) ? readString(submitAction.target) : undefined
}

function findJobCancelActionTarget(resource: RedfishResource): string | undefined {
  if (!isRecord(resource.Actions)) {
    return undefined
  }

  const cancelAction = resource.Actions['#Job.Cancel']
  return isRecord(cancelAction) ? readString(cancelAction.target) : undefined
}

function jobExecutorPath(resource: RedfishResource): string | undefined {
  if (!isRecord(resource.Links)) {
    return undefined
  }

  return toODataPath(resource.Links.Executor)
}

function formatJobActionLabel(actionName: string): string {
  const normalized = actionName.replace(/^#/, '')
  const shortName = normalized.startsWith('Job.') ? normalized.slice(4) : normalized
  return shortName === 'Cancel' ? 'Cancel (Delete Job)' : shortName
}

function isCancelActionName(actionName: string): boolean {
  const normalized = actionName.replace(/^#/, '').toLowerCase()
  return normalized === 'job.cancel' || normalized.endsWith('.cancel') || normalized === 'cancel'
}

function firstSupportedExecutorPath(resource: RedfishResource): string | undefined {
  if (!isRecord(resource.Links) || !Array.isArray(resource.Links.SupportedExecutors)) {
    return undefined
  }

  const executorLink = resource.Links.SupportedExecutors.find((item) => isODataLink(item))
  return executorLink?.['@odata.id']
}

function executorRunningJobs(resource: RedfishResource): ODataLink[] {
  if (!isRecord(resource.Links) || !Array.isArray(resource.Links.ExecutingJobs)) {
    return []
  }

  return resource.Links.ExecutingJobs.filter((item): item is ODataLink => isODataLink(item))
}

function toJobSummary(resource: RedfishResource): JobSummary {
  const state =
    (typeof resource.JobState === 'string' ? resource.JobState : undefined) ??
    (typeof resource.Status?.State === 'string' ? resource.Status.State : 'Unknown')

  const status =
    (typeof resource.JobStatus === 'string' ? resource.JobStatus : undefined) ??
    (typeof resource.Status?.Health === 'string' ? resource.Status.Health : 'Unknown')

  return {
    id: typeof resource.Id === 'string' ? resource.Id : resourceDisplayName(resource),
    name: resourceDisplayName(resource),
    state,
    status,
    percentComplete: typeof resource.PercentComplete === 'number' ? resource.PercentComplete : null,
    createdAt: typeof resource.CreationTime === 'string' ? resource.CreationTime : undefined,
    startTime: typeof resource.StartTime === 'string' ? resource.StartTime : undefined,
    uri: typeof resource['@odata.id'] === 'string' ? resource['@odata.id'] : '',
    raw: resource,
  }
}

function castParameterValue(field: JobDocumentField, input: string): unknown {
  const dataType = field.dataType.toLowerCase()

  if (dataType === 'number' || dataType === 'integer') {
    const numericValue = Number(input)
    if (!Number.isFinite(numericValue)) {
      throw new Error(`Parameter '${field.name}' expects a numeric value.`)
    }
    return numericValue
  }

  if (dataType === 'boolean') {
    if (input.toLowerCase() === 'true') {
      return true
    }
    if (input.toLowerCase() === 'false') {
      return false
    }
    throw new Error(`Parameter '${field.name}' expects true or false.`)
  }

  return input
}

function JobsPage() {
  const { client } = useClient()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const [jobService, setJobService] = useState<RedfishResource | null>(null)
  const [jobDocuments, setJobDocuments] = useState<RedfishResource[]>([])
  const [jobs, setJobs] = useState<JobSummary[]>([])
  const [jobsCollectionPath, setJobsCollectionPath] = useState<string>('')

  const [selectedDocumentUri, setSelectedDocumentUri] = useState<string>('')
  const [selectedJobUri, setSelectedJobUri] = useState<string>('')
  const [formValues, setFormValues] = useState<Record<string, string>>({})
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)
  const [runningJobAction, setRunningJobAction] = useState<string | null>(null)

  const refreshWorkspace = useCallback(async () => {
    try {
      setError(null)

      const root = await client.getServiceRoot()
      const jobServicePath = toODataPath(root.JobService)
      if (!jobServicePath) {
        throw new Error('Service root does not expose JobService.')
      }

      const jobService = await client.getResource(jobServicePath)
      const documentsPath = toODataPath(jobService.JobDocuments)
      const nextJobsPath = toODataPath(jobService.Jobs)

      if (!documentsPath || !nextJobsPath) {
        throw new Error('JobService is missing JobDocuments or Jobs collection links.')
      }

      const [documents, jobsResources] = await Promise.all([
        client.getCollectionMembers(documentsPath),
        client.getCollectionMembers(nextJobsPath),
      ])
      const nextJobs = jobsResources.map(toJobSummary)

      setJobService(jobService)
      setJobDocuments(documents)
      setJobsCollectionPath(nextJobsPath)
      setJobs(nextJobs)

      setSelectedDocumentUri((current) => {
        if (current.length > 0 && documents.some((document) => document['@odata.id'] === current)) {
          return current
        }

        const firstDocumentPath = documents[0]?.['@odata.id']
        return typeof firstDocumentPath === 'string' ? firstDocumentPath : ''
      })

      setSelectedJobUri((current) => {
        if (current.length > 0 && nextJobs.some((job) => job.uri === current)) {
          return current
        }

        return nextJobs[0]?.uri ?? ''
      })
    } catch (workspaceError) {
      const message = workspaceError instanceof Error ? workspaceError.message : 'Failed to load job workspace.'
      setJobService(null)
      setSelectedJobUri('')
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [client])

  useEffect(() => {
    void refreshWorkspace()
  }, [refreshWorkspace])

  const refreshJobs = useCallback(async () => {
    if (!jobsCollectionPath) {
      return
    }

    try {
      const jobsResources = await client.getCollectionMembers(jobsCollectionPath)
      const nextJobs = jobsResources.map(toJobSummary)
      setJobs(nextJobs)
      setSelectedJobUri((current) => {
        if (current.length > 0 && nextJobs.some((job) => job.uri === current)) {
          return current
        }
        return nextJobs[0]?.uri ?? ''
      })
    } catch (jobsError) {
      const message = jobsError instanceof Error ? jobsError.message : 'Unable to refresh jobs list.'
      setError(message)
    }
  }, [client, jobsCollectionPath])

  useEffect(() => {
    if (!jobsCollectionPath) {
      return
    }

    const intervalId = window.setInterval(() => {
      void refreshJobs()
    }, 5000)

    return () => window.clearInterval(intervalId)
  }, [refreshJobs, jobsCollectionPath])

  const selectedDocument = useMemo(
    () => jobDocuments.find((document) => document['@odata.id'] === selectedDocumentUri) ?? null,
    [jobDocuments, selectedDocumentUri],
  )

  const selectedJob = useMemo(() => jobs.find((job) => job.uri === selectedJobUri) ?? null, [jobs, selectedJobUri])
  const selectedJobCancelTarget = useMemo(
    () => (selectedJob ? findJobCancelActionTarget(selectedJob.raw) : undefined),
    [selectedJob],
  )
  const selectedJobActions = useMemo(
    () => (selectedJob ? extractSupportedActions(selectedJob.raw) : []),
    [selectedJob],
  )

  const documentFields = useMemo(() => (selectedDocument ? toDocumentFields(selectedDocument) : []), [selectedDocument])

  useEffect(() => {
    if (!selectedDocument) {
      setFormValues({})
      setFormErrors({})
      return
    }

    setFormValues(buildDefaultValues(documentFields))
    setFormErrors({})
  }, [selectedDocumentUri, selectedDocument, documentFields])

  const setFieldValue = (fieldName: string, value: string) => {
    setFormValues((current) => ({
      ...current,
      [fieldName]: value,
    }))

    setFormErrors((current) => {
      if (!current[fieldName]) {
        return current
      }

      const nextErrors = { ...current }
      delete nextErrors[fieldName]
      return nextErrors
    })
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!selectedDocument || !jobsCollectionPath) {
      setStatusMessage('Select a JobDocument before submitting a job.')
      return
    }

    const nextErrors: Record<string, string> = {}
    const parameterPayload: Record<string, unknown> = {}

    for (const field of documentFields) {
      const rawValue = (formValues[field.name] ?? '').trim()

      if (field.required && rawValue.length === 0) {
        nextErrors[field.name] = `${field.name} is required.`
        continue
      }

      if (rawValue.length === 0) {
        continue
      }

      try {
        parameterPayload[field.name] = castParameterValue(field, rawValue)
      } catch (castError) {
        nextErrors[field.name] = castError instanceof Error ? castError.message : 'Invalid value.'
      }
    }

    if (Object.keys(nextErrors).length > 0) {
      setFormErrors(nextErrors)
      return
    }

    const submitActionTarget = findSubmitJobActionTarget(selectedDocument)
    const executorPath = firstSupportedExecutorPath(selectedDocument)

    if (!executorPath) {
      setStatusMessage('Selected JobDocument does not advertise a supported executor.')
      return
    }

    setIsSubmitting(true)
    setStatusMessage(null)

    try {
      if (submitActionTarget) {
        await client.postAction(submitActionTarget, parameterPayload)
      }

      const executorResource = await client.getResource(executorPath)
      const documentUri = readString(selectedDocument['@odata.id'])
      const nowIso = new Date().toISOString()

      const jobPayload: Record<string, unknown> = {
        '@odata.type': '#Job.v1_3_0.Job',
        Name: `${resourceDisplayName(selectedDocument)} Submitted Job`,
        Description: 'Job submitted from JobDocument form in dashboard.',
        JobType: 'DocumentBased',
        JobState: 'Pending',
        JobStatus: 'OK',
        PercentComplete: 0,
        CreationTime: nowIso,
        StartTime: nowIso,
        Parameters: parameterPayload,
        Links: {
          Executor: {
            '@odata.id': executorPath,
          },
          PreferredExecutors: [
            {
              '@odata.id': executorPath,
            },
          ],
          ValidatedExecutors: [
            {
              '@odata.id': executorPath,
            },
          ],
          ...(documentUri
            ? {
                JobDocument: {
                  '@odata.id': documentUri,
                },
              }
            : {}),
        },
      }

      const createJobResult = await client.postAction(jobsCollectionPath, jobPayload)
      const createdJobPath = createJobResult.headers.get('Location')

      if (createdJobPath) {
        const currentExecutingJobs = executorRunningJobs(executorResource)
        const alreadyLinked = currentExecutingJobs.some((link) => link['@odata.id'] === createdJobPath)

        if (!alreadyLinked) {
          await client.patchResource(executorPath, {
            Links: {
              ExecutingJobs: [...currentExecutingJobs, { '@odata.id': createdJobPath }],
            },
          })
        }
      }

      await refreshJobs()

      setStatusMessage(
        createdJobPath
          ? `Job submitted and created at ${createdJobPath}.`
          : 'Job submitted and job collection updated.',
      )
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : 'Failed to submit job.'
      setStatusMessage(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancelJob = async () => {
    if (!selectedJob || !selectedJob.uri) {
      setStatusMessage('Select a job with a valid URI before canceling.')
      return
    }

    const confirmed = window.confirm(`Cancel and delete job ${selectedJob.name}?`)
    if (!confirmed) {
      return
    }

    setIsCancelling(true)
    setStatusMessage(null)

    try {
      const executorPath = jobExecutorPath(selectedJob.raw)
      if (executorPath) {
        const executorResource = await client.getResource(executorPath)
        const nextExecutingJobs = executorRunningJobs(executorResource).filter(
          (link) => link['@odata.id'] !== selectedJob.uri,
        )

        await client.patchResource(executorPath, {
          Links: {
            ExecutingJobs: nextExecutingJobs,
          },
        })
      }

      const deleteStatus = await client.deleteResource(selectedJob.uri)
      if (deleteStatus >= 400) {
        throw new Error(`Cancel failed. Job delete returned HTTP ${deleteStatus}.`)
      }

      await refreshJobs()
      setStatusMessage(`Job canceled and removed: ${selectedJob.uri}.`)
    } catch (cancelError) {
      const message = cancelError instanceof Error ? cancelError.message : 'Failed to cancel job.'
      setStatusMessage(message)
    } finally {
      setIsCancelling(false)
    }
  }

  const handleExecuteJobAction = async (actionName: string, actionTarget: string) => {
    if (!selectedJob || !selectedJob.uri) {
      setStatusMessage('Select a job with a valid URI before running actions.')
      return
    }

    if (isCancelActionName(actionName)) {
      await handleCancelJob()
      return
    }

    setRunningJobAction(actionName)
    setStatusMessage(null)

    try {
      await client.postAction(actionTarget, {})
      await refreshJobs()
      setStatusMessage(`Action submitted: ${actionName}.`)
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : `Failed to run action ${actionName}.`
      setStatusMessage(message)
    } finally {
      setRunningJobAction(null)
    }
  }

  return (
    <section>
      <header className="page-head">
        <h2 className="page-title">Run a Job</h2>
        <p className="page-subtitle">
          Select a JobDocument, render form fields from <code>ParameterMetadata</code>, then submit a new Job and link it to
          the first supported executor.
        </p>
      </header>

      <div className="panel inline-meta">
        <button className="button-secondary" type="button" onClick={() => void refreshWorkspace()}>
          Refresh Workspace
        </button>
        <button className="button-secondary" type="button" onClick={() => void refreshJobs()} disabled={!jobsCollectionPath}>
          Refresh Jobs
        </button>
        <Link className="button-secondary button-link" to="/explorer?path=/redfish/v1/JobService">
          Open JobService
        </Link>
      </div>

      {loading ? <p className="loading">Loading job service resources...</p> : null}
      {error ? <p className="error-banner">{error}</p> : null}
      {statusMessage ? <p className="success-banner">{statusMessage}</p> : null}

      {jobService ? (
        <div className="panel-grid two-column">
          <article className="panel">
            <h3>JobService Overview</h3>
            <p className="resource-path">{readString(jobService['@odata.id']) ?? '/redfish/v1/JobService'}</p>
            <ResourceTable resource={jobService} />
          </article>

          <SupportedActions resource={jobService} title="JobService Actions (Read Only)" />
        </div>
      ) : null}

      <div className="panel-grid two-column">
        <article className="panel">
          <h3>JobDocument Collection</h3>
          {jobDocuments.length === 0 ? <p className="muted">No JobDocuments discovered.</p> : null}
          <div className="list-stack">
            {jobDocuments.map((document) => {
              const uri = readString(document['@odata.id']) ?? resourceDisplayName(document)
              const selected = selectedDocumentUri === uri

              return (
                <button
                  type="button"
                  key={uri}
                  className={`resource-card selectable ${selected ? 'selected' : ''}`}
                  onClick={() => setSelectedDocumentUri(uri)}
                >
                  <div className="card-head">
                    <h4>{resourceDisplayName(document)}</h4>
                    <StatusPill tone={getStatusTone(document.Status)} label={document.Status?.State ?? 'Unknown'} />
                  </div>
                  <p>Type: {typeof document.DocumentType === 'string' ? document.DocumentType : 'Unknown'}</p>
                  <p className="resource-path">{uri}</p>
                </button>
              )
            })}
          </div>
        </article>

        <article className="panel">
          <h3>Submit Job Form</h3>
          {!selectedDocument ? <p className="muted">Choose a JobDocument to build the form.</p> : null}

          {selectedDocument ? (
            <form className="form-grid" onSubmit={handleSubmit}>
              {documentFields.length === 0 ? <p className="muted">No parameters required by this JobDocument.</p> : null}

              {documentFields.map((field) => {
                const value = formValues[field.name] ?? ''
                const errorMessage = formErrors[field.name]
                const key = `${selectedDocumentUri}-${field.name}`
                const dataType = field.dataType.toLowerCase()

                return (
                  <label className="field" key={key}>
                    <span className="field-label">
                      {field.name} ({field.dataType}){field.required ? ' *' : ''}
                    </span>

                    {field.allowableValues.length > 0 ? (
                      <select
                        className="field-select"
                        value={value}
                        onChange={(event) => setFieldValue(field.name, event.target.value)}
                        required={field.required}
                      >
                        {!field.required ? <option value="">(blank)</option> : null}
                        {field.allowableValues.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        className="field-input"
                        type={dataType === 'number' || dataType === 'integer' ? 'number' : 'text'}
                        value={value}
                        onChange={(event) => setFieldValue(field.name, event.target.value)}
                        required={field.required}
                        placeholder={field.valueHint}
                      />
                    )}

                    {field.description ? <span className="muted">{field.description}</span> : null}
                    {errorMessage ? <span className="error-banner inline-error">{errorMessage}</span> : null}
                  </label>
                )
              })}

              <button className="button-primary" type="submit" disabled={isSubmitting || !jobsCollectionPath}>
                {isSubmitting ? 'Submitting...' : 'SubmitJob'}
              </button>
            </form>
          ) : null}
        </article>
      </div>

      {selectedDocument ? (
        <div className="panel-grid two-column">
          <article className="panel">
            <h3>Selected JobDocument Details</h3>
            <ResourceTable resource={selectedDocument} />
            <p className="resource-path top-space-sm">Executor: {firstSupportedExecutorPath(selectedDocument) ?? 'N/A'}</p>
          </article>

          <SupportedActions resource={selectedDocument} title="Supported Actions (Read Only)" />

          <article className="panel two-column-span">
            <JsonPanel title="Selected JobDocument JSON" data={selectedDocument} />
          </article>
        </div>
      ) : null}

      <article className="panel">
        <h3>Jobs Collection</h3>
        {jobs.length === 0 ? <p className="muted">No jobs currently listed.</p> : null}

        <div className="card-grid">
          {jobs.map((job) => {
            const cardKey = job.uri.length > 0 ? job.uri : `${job.id}-${job.createdAt ?? 'n/a'}`
            const selected = selectedJobUri === job.uri

            return (
            <button
              type="button"
              key={cardKey}
              className={`resource-card selectable ${selected ? 'selected' : ''}`}
              onClick={() => setSelectedJobUri(job.uri)}
              disabled={job.uri.length === 0}
            >
              <div className="card-head">
                <h4>{job.name}</h4>
                <StatusPill tone={getStatusTone({ State: job.state, Health: job.status })} label={job.state} />
              </div>
              <p>JobStatus: {job.status}</p>
              <p>PercentComplete: {job.percentComplete ?? 'N/A'}</p>
              <p>Created: {formatIsoDate(job.createdAt)}</p>
              <p>Started: {formatIsoDate(job.startTime)}</p>
              <p className="resource-path">{job.uri}</p>
            </button>
            )
          })}
        </div>
      </article>

      {selectedJob ? (
        <div className="panel-grid two-column">
          <article className="panel">
            <h3>Selected Job Details</h3>
            <ResourceTable resource={selectedJob.raw} />
            <p className="resource-path top-space-sm">Cancel target: {selectedJobCancelTarget ?? 'Not advertised'}</p>
          </article>

          <article className="panel">
            <h3>Job Action Controls</h3>
            {selectedJobActions.length === 0 ? <p className="muted">No actions advertised by this job resource.</p> : null}
            <div className="action-list">
              {selectedJobActions.map((action) => (
                <div className="action-item" key={`${action.name}-${action.target}`}>
                  <p className="action-name">{action.name}</p>
                  <p className="resource-path">{action.target}</p>
                  <button
                    className="button-secondary"
                    type="button"
                    onClick={() => void handleExecuteJobAction(action.name, action.target)}
                    disabled={isCancelling || runningJobAction !== null || !selectedJob.uri}
                  >
                    {runningJobAction === action.name
                      ? 'Running...'
                      : isCancelling && action.name === '#Job.Cancel'
                        ? 'Canceling...'
                        : formatJobActionLabel(action.name)}
                  </button>
                </div>
              ))}
            </div>
          </article>

          <SupportedActions resource={selectedJob.raw} title="Selected Job Actions (Read Only)" />
        </div>
      ) : null}
    </section>
  )
}

export default JobsPage
