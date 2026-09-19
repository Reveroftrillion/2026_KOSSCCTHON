import TripHome from '@/components/fe2/TripHome'

export default async function TripHomePage({ params }: PageProps<'/trips/[tripId]'>) {
  const { tripId } = await params
  return <TripHome tripId={tripId} />
}
