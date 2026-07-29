import React, { useRef, useState } from 'react';
import { FolderPlus } from 'lucide-react';
import { projectsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Modal from './ui/Modal';
import Alert from './ui/Alert';
import Button from './ui/Button';
import TextField from './ui/TextField';
import { useSubmit } from '../hooks/useSubmit';

export const CreateProjectModal = ({ isOpen, onClose, onProjectCreated }) => {
  const { student } = useAuth();
  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const nameRef = useRef(null);

  const { submit, submitting, error } = useSubmit(
    () =>
      projectsAPI.create({
        student_id: student.student_id,
        project_name: projectName.trim(),
        description: description.trim(),
      }),
    {
      validate: () => !projectName.trim() && 'Project name is required.',
      onSuccess: (newProject) => {
        onProjectCreated(newProject);
        setProjectName('');
        setDescription('');
        onClose();
      },
      fallbackError: 'Failed to create project. Please try again.',
    }
  );

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      title="Create New Project"
      description="Set up a portfolio or academic project to analyse"
      icon={FolderPlus}
      initialFocusRef={nameRef}
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="create-project-form"
            size="md"
            icon={FolderPlus}
            loading={submitting}
            loadingText="Creating…"
          >
            Create Project
          </Button>
        </>
      }
    >
      {error ? <Alert tone="error">{error}</Alert> : null}

      {/* The submit button lives in the Modal footer, outside this form element,
          so it is associated by id via the form attribute. */}
      <form id="create-project-form" onSubmit={submit} noValidate className="space-y-4">
        <TextField
          ref={nameRef}
          label="Project Name"
          name="project_name"
          required
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="e.g. AI Resume Analyser & Matcher"
          disabled={submitting}
        />

        <TextField
          as="textarea"
          rows={3}
          label="Description / Summary"
          name="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Briefly describe the key technologies, domain, or target goals of this project…"
          inputClassName="resize-none"
          disabled={submitting}
        />
      </form>
    </Modal>
  );
};

export default CreateProjectModal;
