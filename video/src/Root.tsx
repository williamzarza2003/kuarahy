import { Composition } from 'remotion'
import { DURACION, Spot } from './Spot'
import { fuentesListas } from './marca'

// Espera las fuentes antes del primer cuadro (el grabado se dibuja en un canvas con la tipografía de la marca)
void fuentesListas

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Spot-16x9"
        component={Spot}
        durationInFrames={DURACION}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ web: 'kuarahy.vercel.app', nombreGrabado: 'Ña Rosa' }}
      />
      <Composition
        id="Spot-9x16"
        component={Spot}
        durationInFrames={DURACION}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ web: 'kuarahy.vercel.app', nombreGrabado: 'Ña Rosa' }}
      />
    </>
  )
}
