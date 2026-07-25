import React, { useState } from 'react';
import { resumesAPI } from '../services/api';
import { X, UploadCloud, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

export const ResumeUploadModal = ({ isOpen, onClose, project, onResumeUploaded }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  if (!isOpen || !project) return null;

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    validateAndSetFile(file);
  };

  const validateAndSetFile = (file) => {
    setError('');
    if (!file) return;

    const allowedTypes = ['.pdf', '.docx'];
    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!allowedTypes.includes(extension)) {
      setError('Unsupported file type. Please upload a PDF or DOCX resume.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('File size exceeds the 10MB limit.');
      return;
    }

    setSelectedFile(file);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!selectedFile) {
      setError('Please select a resume file to upload.');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('project_id', project.project_id);
      formData.append('resume_file', selectedFile);

      const response = await resumesAPI.upload(formData);
      onResumeUploaded(response);
      setSelectedFile(null);
      onClose();
    } catch (err) {
      console.error('Resume upload failed:', err);
      const apiError = err.response?.data?.error || err.response?.data?.detail || 'Failed to upload resume.';
      setError(apiError);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-lg glass-panel rounded-2xl p-6 shadow-2xl border border-slate-800 relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-button flex items-center justify-center">
              <UploadCloud className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Upload Resume</h3>
              <p className="text-xs text-slate-400">Target Project: <span className="text-brand-300 font-semibold">{project.project_name}</span></p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-red-950/60 border border-red-800/60 text-red-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <div>{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Dropzone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
              dragActive
                ? 'border-brand-500 bg-brand-950/40 scale-[1.01]'
                : selectedFile
                ? 'border-emerald-500/50 bg-emerald-950/20'
                : 'border-slate-700/80 bg-slate-900/40 hover:border-slate-600'
            }`}
          >
            <input
              type="file"
              id="resume-file-input"
              accept=".pdf,.docx"
              onChange={handleFileChange}
              className="hidden"
            />

            {selectedFile ? (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3">
                  <CheckCircle2 className="w-7 h-7" />
                </div>
                <div className="text-sm font-semibold text-white">{selectedFile.name}</div>
                <div className="text-xs text-slate-400 mt-1">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </div>
                <label
                  htmlFor="resume-file-input"
                  className="mt-3 text-xs text-brand-400 hover:text-brand-300 font-semibold cursor-pointer underline underline-offset-2"
                >
                  Choose another file
                </label>
              </div>
            ) : (
              <label htmlFor="resume-file-input" className="cursor-pointer block">
                <div className="w-12 h-12 rounded-xl bg-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-3">
                  <FileText className="w-6 h-6" />
                </div>
                <div className="text-sm font-semibold text-slate-200">
                  Click to browse or drag & drop resume here
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Supports PDF and DOCX formats (Up to 10MB)
                </div>
              </label>
            )}
          </div>

          <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="px-5 py-2.5 rounded-xl gradient-button text-white font-semibold text-xs flex items-center gap-2 disabled:opacity-50"
            >
              <UploadCloud className="w-4 h-4" />
              {uploading ? 'Uploading & Parsing...' : 'Upload Resume'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ResumeUploadModal;
