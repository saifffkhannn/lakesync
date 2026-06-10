import { useEffect, useMemo, useRef, useState } from "react"
import type { KeyboardEvent } from "react"
import { useNavigate } from "react-router-dom"
import { FaEye, FaEyeSlash } from "react-icons/fa"
import { ArrowLeft, Save, Settings2 } from "lucide-react"
import RegionCombobox from "../components/RegionCombobox"
import DashboardLayout from "../components/dashboard/DashboardLayout"
import { cloudRegions } from "../data/cloudRegions"
import ThemedSelect from "../components/ThemedSelect"

type ConfigMap = Record<string, Record<string, string>>
type FormValues = Record<string, string>
type FormValuesBySelection = Record<string, FormValues>

const getSavedFormsBySelection = (key: string): FormValuesBySelection => {
  const savedValue = sessionStorage.getItem(key)

  if (!savedValue) {
    return {}
  }

  try {
    return JSON.parse(savedValue) as FormValuesBySelection
  } catch {
    return {}
  }
}

const getSavedSelection = (key: string) => {
  return sessionStorage.getItem(key) || localStorage.getItem(key) || ""
}

const buildOrderedValues = (fields: string[], values: FormValues) =>
  fields.reduce<FormValues>((accumulator, field) => {
    accumulator[field] = values[field] || ""
    return accumulator
  }, {})

const Connection = () => {
  const navigate = useNavigate()
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})

  const [sourceConfig, setSourceConfig] = useState<ConfigMap>({})
  const [cloudConfig, setCloudConfig] = useState<ConfigMap>({})
  const [targetConfig, setTargetConfig] = useState<ConfigMap>({})

  const [selectedSource, setSelectedSource] = useState("")
  const [selectedCloud, setSelectedCloud] = useState("")
  const [selectedTarget, setSelectedTarget] = useState("")

  const [sourceForms, setSourceForms] = useState<FormValuesBySelection>(() =>
    getSavedFormsBySelection("sourceForms")
  )
  const [cloudForms, setCloudForms] = useState<FormValuesBySelection>(() =>
    getSavedFormsBySelection("cloudForms")
  )
  const [targetForms, setTargetForms] = useState<FormValuesBySelection>(() =>
    getSavedFormsBySelection("targetForms")
  )

  const [showField, setShowField] = useState<{ [key: string]: boolean }>({})

  const [showMapperButton, setShowMapperButton] = useState(false)
  const [toast, setToast] = useState("")

  const sourceData = useMemo(
    () => sourceForms[selectedSource] || {},
    [selectedSource, sourceForms]
  )
  const cloudData = useMemo(
    () => cloudForms[selectedCloud] || {},
    [cloudForms, selectedCloud]
  )
  const targetData = useMemo(
    () => targetForms[selectedTarget] || {},
    [selectedTarget, targetForms]
  )

  const sourceFields = useMemo(
    () => (selectedSource ? Object.keys(sourceConfig[selectedSource] || {}) : []),
    [selectedSource, sourceConfig]
  )

  const cloudFields = useMemo(
    () => (selectedCloud ? Object.keys(cloudConfig[selectedCloud] || {}) : []),
    [selectedCloud, cloudConfig]
  )

  const targetFields = useMemo(
    () =>
      selectedTarget
        ? Object.keys(targetConfig[selectedTarget] || {}).filter((field) => {
            if (field === "managed_location" && selectedCloud !== "AZURE") {
              return false
            }
            return true
          })
        : [],
    [selectedCloud, selectedTarget, targetConfig]
  )

  const fieldOrder = useMemo(
    () => [
      ...sourceFields.map((field) => `source-${field}`),
      ...cloudFields.map((field) => `cloud-${field}`),
      ...targetFields.map((field) => `target-${field}`),
    ],
    [sourceFields, cloudFields, targetFields]
  )

  const focusRelativeField = (currentFieldId: string, direction: 1 | -1) => {
    const currentIndex = fieldOrder.indexOf(currentFieldId)
    const nextFieldId = fieldOrder[currentIndex + direction]

    if (nextFieldId) {
      fieldRefs.current[nextFieldId]?.focus()
    }
  }

  const handleFieldKeyDown = (
    event: KeyboardEvent<HTMLInputElement>,
    currentFieldId: string
  ) => {
    if (event.key === "ArrowDown" || event.key === "Enter") {
      event.preventDefault()
      focusRelativeField(currentFieldId, 1)
    }

    if (event.key === "ArrowUp") {
      event.preventDefault()
      focusRelativeField(currentFieldId, -1)
    }
  }

  useEffect(() => {
    fetch("/configuration/source.json")
      .then((res) => res.json())
      .then((data) => {
        setSourceConfig(data)
        const keys = Object.keys(data)
        const savedSelection = getSavedSelection("selectedSource")
        setSelectedSource(keys.includes(savedSelection) ? savedSelection : keys[0] || "")
      })

    fetch("/configuration/cloud.json")
      .then((res) => res.json())
      .then((data) => {
        setCloudConfig(data)
        const keys = Object.keys(data)
        const savedSelection = getSavedSelection("selectedCloud")
        setSelectedCloud(keys.includes(savedSelection) ? savedSelection : keys[0] || "")
      })

    fetch("/configuration/target.json")
      .then((res) => res.json())
      .then((data) => {
        setTargetConfig(data)
        const keys = Object.keys(data)
        const savedSelection = getSavedSelection("selectedTarget")
        setSelectedTarget(keys.includes(savedSelection) ? savedSelection : keys[0] || "")
      })
  }, [])

  const handleChange = (type: string, field: string, value: string) => {
    if (type === "source") {
      setSourceForms((previous) => ({
        ...previous,
        [selectedSource]: {
          ...(previous[selectedSource] || {}),
          [field]: value,
        },
      }))
    }

    if (type === "cloud") {
      setCloudForms((previous) => ({
        ...previous,
        [selectedCloud]: {
          ...(previous[selectedCloud] || {}),
          [field]: value,
        },
      }))
    }

    if (type === "target") {
      setTargetForms((previous) => ({
        ...previous,
        [selectedTarget]: {
          ...(previous[selectedTarget] || {}),
          [field]: value,
        },
      }))
    }
  }

  useEffect(() => {
    sessionStorage.setItem("sourceForms", JSON.stringify(sourceForms))
  }, [sourceForms])

  useEffect(() => {
    sessionStorage.setItem("cloudForms", JSON.stringify(cloudForms))
  }, [cloudForms])

  useEffect(() => {
    sessionStorage.setItem("targetForms", JSON.stringify(targetForms))
  }, [targetForms])

  useEffect(() => {
    if (!selectedSource) {
      return
    }

    sessionStorage.setItem("selectedSource", selectedSource)
    localStorage.setItem("selectedSource", selectedSource)
  }, [selectedSource])

  useEffect(() => {
    if (!selectedCloud) {
      return
    }

    sessionStorage.setItem("selectedCloud", selectedCloud)
    localStorage.setItem("selectedCloud", selectedCloud)
  }, [selectedCloud])

  useEffect(() => {
    if (!selectedTarget) {
      return
    }

    sessionStorage.setItem("selectedTarget", selectedTarget)
    localStorage.setItem("selectedTarget", selectedTarget)
  }, [selectedTarget])

  const isSensitiveField = (field: string) => {
    const sensitiveKeywords = ["password", "secret", "token", "key"]

    return sensitiveKeywords.some((keyword) =>
      field.toLowerCase().includes(keyword)
    )
  }

  const handleSaveConfiguration = async () => {
    const orderedSourceData = buildOrderedValues(sourceFields, sourceData)
    const orderedCloudData = buildOrderedValues(cloudFields, cloudData)
    const orderedTargetData = buildOrderedValues(targetFields, targetData)

    const sourceDataFormatted = {
      [selectedSource.toLowerCase()]: orderedSourceData,
    }

    const payload = {
      source: selectedSource.toLowerCase(),
      cloud: selectedCloud.toLowerCase(),
      target: selectedTarget.toLowerCase(),
      data: {
        ...sourceDataFormatted,
        [selectedCloud.toLowerCase()]: orderedCloudData,
        [selectedTarget.toLowerCase()]: orderedTargetData,
      },
    }

    try {
      const response = await fetch("http://localhost:8000/save-credentials", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })

      const res = await response.json()

      if (response.ok) {
        setToast("Configuration saved successfully!")
        setShowMapperButton(true)

        setTimeout(() => {
          setToast("")
        }, 3000)
      } else {
        setToast(`Error: ${res.detail || "Failed to save configuration"}`)
        setTimeout(() => {
          setToast("")
        }, 3000)
      }
    } catch {
      setToast("Network error. Is the backend running?")
      setTimeout(() => {
        setToast("")
      }, 3000)
    }
  }

  return (
    <DashboardLayout showSearch={true}>
      {toast && (
        <div className="fixed right-6 top-24 z-50 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-medium text-white shadow-2xl shadow-emerald-600/20">
          {toast}
        </div>
      )}

      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-start rounded-2xl border border-gray-100 bg-white/80 px-5 py-4 shadow-sm dark:border-gray-800 dark:bg-gray-900/70">
          <div className="min-w-0">
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400">
              <Settings2 className="h-4 w-4" />
              Connections
            </p>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              Data Migration Configuration
            </h1>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <section className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm shadow-gray-200/50 transition-colors duration-300 dark:border-gray-700/50 dark:bg-gray-900/75 dark:shadow-black/10 ">
            <h2 className="mb-1 text-xl font-semibold text-blue-600 dark:text-blue-400">
              Source
            </h2>
            <ThemedSelect
              accent="blue"
              value={selectedSource}
              options={Object.keys(sourceConfig)}
              onChange={setSelectedSource}
              placeholder="Choose source..."
            />


            {sourceFields.map((field) => (
              <div key={field} className="relative">
                <input
                  ref={(element) => {
                    fieldRefs.current[`source-${field}`] = element
                  }}
                  className="mb-3 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 pr-11 text-sm text-gray-700 outline-none transition-all duration-200 focus:border-blue-300 focus:bg-white focus:ring-2 focus:ring-blue-500/20 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-blue-600"
                  placeholder={field}
                  value={sourceData[field] || ""}
                  type={isSensitiveField(field) && !showField[`source-${field}`] ? "password" : "text"}
                  onChange={(e) => handleChange("source", field, e.target.value)}
                  onKeyDown={(e) => handleFieldKeyDown(e, `source-${field}`)}
                />
                {isSensitiveField(field) && (
                  <button
                    type="button"
                    onClick={() =>
                      setShowField({
                        ...showField,
                        [`source-${field}`]: !showField[`source-${field}`],
                      })
                    }
                    className="absolute right-3 top-3 text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                  >
                    {showField[`source-${field}`] ? <FaEyeSlash /> : <FaEye />}
                  </button>
                )}
              </div>
            ))}
          </section>

          <section className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm shadow-gray-200/50 transition-colors duration-300 dark:border-gray-700/50 dark:bg-gray-900/75 dark:shadow-black/10 ">
            <h2 className="mb-1 text-xl font-semibold text-emerald-600 dark:text-emerald-400">
              Cloud
            </h2>
            <ThemedSelect
              accent="emerald"
              value={selectedCloud}
              options={Object.keys(cloudConfig)}
              onChange={setSelectedCloud}
              placeholder="Choose cloud..."
            />

            {cloudFields.map((field) => (
              <div key={field} className="relative">
                {field === "aws_region" ? (
                  <RegionCombobox
                    ref={(element) => {
                      fieldRefs.current[`cloud-${field}`] = element
                    }}
                    placeholder={field}
                    value={cloudData[field] || ""}
                    options={cloudRegions[selectedCloud] || []}
                    onChange={(value) => handleChange("cloud", field, value)}
                    onFormKeyDown={(e) => handleFieldKeyDown(e, `cloud-${field}`)}
                  />
                ) : (
                  <input
                    ref={(element) => {
                      fieldRefs.current[`cloud-${field}`] = element
                    }}
                    className="mb-3 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 pr-11 text-sm text-gray-700 outline-none transition-all duration-200 focus:border-emerald-300 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-emerald-600"
                    placeholder={field}
                    value={cloudData[field] || ""}
                    type={isSensitiveField(field) && !showField[`cloud-${field}`] ? "password" : "text"}
                    onChange={(e) => handleChange("cloud", field, e.target.value)}
                    onKeyDown={(e) => handleFieldKeyDown(e, `cloud-${field}`)}
                  />
                )}
                {field !== "aws_region" && isSensitiveField(field) && (
                  <button
                    type="button"
                    onClick={() =>
                      setShowField({
                        ...showField,
                        [`cloud-${field}`]: !showField[`cloud-${field}`],
                      })
                    }
                    className="absolute right-3 top-3 text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                  >
                    {showField[`cloud-${field}`] ? <FaEyeSlash /> : <FaEye />}
                  </button>
                )}
              </div>
            ))}
          </section>

          <section className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm shadow-gray-200/50 transition-colors duration-300 dark:border-gray-700/50 dark:bg-gray-900/75 dark:shadow-black/10 ">
            <h2 className="mb-1 text-xl font-semibold text-violet-600 dark:text-violet-400">
              Target
            </h2>
            <ThemedSelect
              accent="violet"
              value={selectedTarget}
              options={Object.keys(targetConfig)}
              onChange={setSelectedTarget}
              placeholder="Choose target..."
            />

            {targetFields.map((field) => (
              <div key={field} className="relative">
                <input
                  ref={(element) => {
                    fieldRefs.current[`target-${field}`] = element
                  }}
                  className="mb-3 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 pr-11 text-sm text-gray-700 outline-none transition-all duration-200 focus:border-violet-300 focus:bg-white focus:ring-2 focus:ring-violet-500/20 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-violet-600"
                  placeholder={field}
                  value={targetData[field] || ""}
                  type={isSensitiveField(field) && !showField[`target-${field}`] ? "password" : "text"}
                  onChange={(e) => handleChange("target", field, e.target.value)}
                  onKeyDown={(e) => handleFieldKeyDown(e, `target-${field}`)}
                />
                {isSensitiveField(field) && (
                  <button
                    type="button"
                    onClick={() =>
                      setShowField({
                        ...showField,
                        [`target-${field}`]: !showField[`target-${field}`],
                      })
                    }
                    className="absolute right-3 top-3 text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                  >
                    {showField[`target-${field}`] ? <FaEyeSlash /> : <FaEye />}
                  </button>
                )}
              </div>
            ))}
          </section>
        </div>
        
        <div className="flex w-full items-center justify-center gap-4 pt-6">
          <button
            id="back-to-dashboard"
            onClick={() => navigate("/dashboard")}
            className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-600 transition-all duration-200 hover:-translate-y-0.5 hover:bg-gray-50 hover:shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-800/80"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </button>

          <button
            onClick={handleSaveConfiguration}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:-translate-y-0.5 hover:from-blue-700 hover:to-blue-600 hover:shadow-blue-500/30"
          >
            <Save className="h-4 w-4" />
            Save Configuration
          </button>

          {showMapperButton && (
            <button
              onClick={() => navigate("/mapper")}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-emerald-700"
            >
              Go To Source Mapper
            </button>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}

export default Connection
