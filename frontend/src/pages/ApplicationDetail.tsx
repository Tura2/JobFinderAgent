import { useParams, useNavigate } from "react-router-dom";

export default function ApplicationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  return (
    <div className="pb-20 pt-4 px-4">
      <button onClick={() => navigate("/tracker")} className="text-blue-400 text-sm mb-4">
        &larr; Back to Tracker
      </button>
      <h1 className="text-xl font-bold mb-4">Application #{id}</h1>
      <p className="text-gray-400">Detailed view coming soon.</p>
    </div>
  );
}
