{{- define "ei.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ei.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "ei.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ei.labels" -}}
app.kubernetes.io/name: {{ include "ei.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "ei.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "ei.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "ei.image" -}}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag -}}
{{- end -}}

{{- define "ei.s3EndpointUrl" -}}
{{- if .Values.artifactStore.endpointUrl -}}
{{- .Values.artifactStore.endpointUrl -}}
{{- else if .Values.seaweedfs.enabled -}}
{{- printf "http://%s-seaweedfs:8333" (include "ei.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "ei.env" -}}
- name: EI_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ required "existingSecret must name the Secret that holds EI_DATABASE_URL" .Values.existingSecret }}
      key: EI_DATABASE_URL
- name: EI_RABBITMQ_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.existingSecret }}
      key: EI_RABBITMQ_URL
- name: EI_API_KEYS
  valueFrom:
    secretKeyRef:
      name: {{ .Values.existingSecret }}
      key: EI_API_KEYS
{{- if eq .Values.artifactStore.kind "s3" }}
- name: EI_S3_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.existingSecret }}
      key: EI_S3_ACCESS_KEY_ID
- name: EI_S3_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.existingSecret }}
      key: EI_S3_SECRET_ACCESS_KEY
{{- end }}
{{- end -}}

