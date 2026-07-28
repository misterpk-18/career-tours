import React, { useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { resumesAPI } from '../services/api';
import Modal from './ui/Modal';
import Alert from './ui/Alert';
import Button from './ui/Button';
import FileDropzone from './ui/FileDropzone';
import { useSubmit } from '../hooks/useSubmit';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];
const MAX_BYTES = 10 * 1024 * 1024;

export const ResumeUploadModal = ({ isOpen, onClose, project, onResumeUploaded }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState('');

  const { submit, submitting, error, setError } = useSubmit(
    () => {
      const formData = new FormData();
      formData.append('project_id', project.project_id);
      formData.append('resume_file', selectedFile);
      return resumesAPI.upload(formData);
    },
    {
      validate: () => !selectedFile && 'Please select a resume file to upload.',
      onSuccess: (response) => {
        onResumeUploaded(response);
        setSelectedFile(null);
        onClose();
      },
      fallbackError: 'Failed to upload resume.',
    }
  );

  const acceptFile = (file) => {
    setFileError('');
    setError('');
    if (!file) return;

    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setFileError('Unsupported file type. Please upload a PDF or DOCX resume.');
      return;
    }
    if (file.size > MAX_BYTES) {
      setFileError('File size exceeds the 10MB limit.');
      return;
    }

    setSelectedFile(file);
  };

  if (!project) return null;

  const shownError = error || fileError;

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      title="Upload Resume"
      description={project.project_name}
      icon={UploadCloud}
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="resume-upload-form"
            size="md"
            icon={UploadCloud}
            loading={submitting}
            loadingText="Uploading…"
            disabled={!selectedFile}
          >
            Upload Resume
          </Button>
        </>
      }
    >
      {shownError ? <Alert tone="error">{shownError}</Alert> : null}

      <form id="resume-upload-form" onSubmit={submit} noValidate>
        <FileDropzone
          accept=".pdf,.docx"
          file={selectedFile}
          onFileSelected={acceptFile}
          onClear={() => setSelectedFile(null)}
          hint="PDF or DOCX, up to 10MB."
          error={!!fileError}
        />
      </form>
    </Modal>
  );
};

export default ResumeUploadModal;
